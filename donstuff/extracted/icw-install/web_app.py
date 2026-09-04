#!/usr/bin/env python3
"""Web front end for the iCluster-web installer.

This is an alternative presentation layer for the existing curses wizard
(app.py / frame.py / page.py / item.py). It reads the same step/page
configuration (icw-install.json or icw-upgrade.json) and drives the exact
same business logic in tools/*_model.py + tools/func_param.py - only the
UI (curses -> HTML over HTTP) is different.

Usage (run from this directory, same as app.py):
    /QOpenSys/pkgs/bin/python3.6 web_app.py install
    /QOpenSys/pkgs/bin/python3.6 web_app.py upgrade --host 0.0.0.0 --port 8090

Notes:
  - Uses only the Python standard library (no Flask/etc.) so no extra
    packages need to be installed on the target IBM i system.
  - Binds to 127.0.0.1 by default. This tool has no authentication, so it
    is meant to be used locally or over an already-trusted admin network -
    pass --host explicitly if you need to expose it more broadly.
  - Single-installer-run-at-a-time, matching the original curses tool: all
    wizard state lives in this one process, in memory.
"""
import argparse
import html
import importlib.util
import json
import logging
import os
import re
import sys
import threading
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from urllib.parse import parse_qs, urlparse

import icwconfig
from icwconfig import _

CONFIG_FILES = {'install': 'icw-install.json', 'upgrade': 'icw-upgrade.json'}

# ---------------------------------------------------------------------------
# Model loading - mirrors item.py's `imp.load_source(...)` + `GetModel()`
# ---------------------------------------------------------------------------
_loaded_modules = {}
_module_lock = threading.Lock()


def load_model_module(model_path):
    with _module_lock:
        module = _loaded_modules.get(model_path)
        if module is None:
            spec = importlib.util.spec_from_file_location(model_path, model_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            _loaded_modules[model_path] = module
    return module


class ModelLoadError(Exception):
    pass


def get_model_instance(step):
    if 'model' not in step:
        return None
    try:
        module = load_model_module(step['model'])
    except Exception as exc:  # noqa: BLE001 - e.g. missing psycopg2/paramiko/ibm_db on this host
        raise ModelLoadError(
            'Could not load {0}: {1}: {2}'.format(step['model'], exc.__class__.__name__, exc)
        )
    if hasattr(module, 'GetModel'):
        return getattr(module, 'GetModel')()
    return None


import tools.func_param as func_param  # noqa: E402  (needs cwd on sys.path first)


# ---------------------------------------------------------------------------
# Output window adapter - mirrors the curses addstr()/refresh()/scrollok()
# surface that tools/*_model.py already calls on `outputWin`.
# ---------------------------------------------------------------------------
class WebOutputWindow:
    def __init__(self):
        self._lines = []
        self._lock = threading.Lock()

    def addstr(self, *args):
        text = args[-1] if args else ''
        with self._lock:
            self._lines.append(str(text))

    def refresh(self):
        pass

    def scrollok(self, _flag):
        pass

    def snapshot(self, offset=0):
        with self._lock:
            return list(self._lines[offset:]), len(self._lines)


class Job:
    """Runs a single model function on a background thread so the browser
    can poll for incremental console output instead of blocking on a
    potentially long-running install/upgrade/uninstall action."""

    def __init__(self, func, param):
        self.id = uuid.uuid4().hex
        self.output = WebOutputWindow()
        self.done = False
        self.result = None
        self._thread = threading.Thread(target=self._run, args=(func, param), daemon=True)

    def start(self):
        self._thread.start()
        return self

    def _run(self, func, param):
        try:
            self.result = bool(func(param))
        except Exception as exc:  # noqa: BLE001 - surface any failure to the console panel
            logging.exception('action failed')
            self.output.addstr('\n*** Error: {}: {}\n'.format(exc.__class__.__name__, exc))
            self.result = False
        finally:
            self.done = True


jobs = {}
jobs_lock = threading.Lock()

# per (stepIdx, pageIdx) runtime state: console output + whether the action succeeded
page_runtime = {}
runtime_lock = threading.Lock()


def get_page_state(s, p):
    key = (s, p)
    with runtime_lock:
        state = page_runtime.get(key)
        if state is None:
            state = {'output': WebOutputWindow(), 'unlocked': False, 'job': None}
            page_runtime[key] = state
        return state


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
class Wizard:
    def __init__(self, mode):
        self.mode = mode
        path = CONFIG_FILES[mode]
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
        with open(path, encoding='utf-8') as f:
            self.config = json.load(f)

    @property
    def steps(self):
        return self.config['steps']

    @property
    def label(self):
        return self.config.get('label', 'iCluster-web installer')

    def step_page(self, s, p):
        step = self.steps[s]
        page = step['pages'][p]
        return step, page


# ---------------------------------------------------------------------------
# Field helpers - mirrors item.py's refreshFromModel()/updateModel()
# ---------------------------------------------------------------------------
def is_visible(step, model):
    return True


def page_is_visible(page, model):
    funcname = page.get('visiblefunc')
    if not funcname or model is None or not hasattr(model, funcname):
        return True
    try:
        return bool(getattr(model, funcname)())
    except Exception:
        logging.exception('visiblefunc %s failed', funcname)
        return True


def field_current_value(model, item):
    modelprop = item.get('modelprop')
    if item['type'] == 'checkbox':
        value = getattr(model, modelprop, None) if model and modelprop else None
        if value is None:
            value = item.get('defaultValue', False)
        return bool(value)

    if item['type'] == 'password':
        # Never echo stored passwords back into the page; just remember
        # whether one is already set so the UI can hint at that.
        has_value = bool(model and modelprop and getattr(model, modelprop, None))
        return '', has_value

    value = getattr(model, modelprop, None) if model and modelprop else None
    if value in (None, ''):
        value = item.get('defaultValue', '')
        if model is not None and modelprop:
            setattr(model, modelprop, value)
    return value


def validate_field(item, raw_value):
    if item['type'] == 'password' and not raw_value:
        return True, None  # blank means "keep existing value"
    regex = item.get('regex')
    if regex and not re.match(regex, raw_value):
        return False, 'Invalid value for "{}"'.format(item['label'].strip())
    maxlen = item.get('maxlen')
    if maxlen and len(raw_value) > maxlen:
        return False, '"{}" exceeds max length of {}'.format(item['label'].strip(), maxlen)
    return True, None


def apply_form_to_model(model, items, form):
    errors = []
    action_item = None
    for item in items:
        itype = item['type']
        if itype == 'button':
            action_item = item
            continue
        if itype in ('label', 'dummy'):
            continue
        modelprop = item.get('modelprop')
        if not modelprop or item.get('editable') is False:
            continue
        if itype == 'checkbox':
            if model is not None:
                setattr(model, modelprop, modelprop in form)
            continue
        raw_value = form.get(modelprop, [''])[0]
        ok, err = validate_field(item, raw_value)
        if not ok:
            errors.append(err)
            continue
        if itype == 'password' and not raw_value:
            continue  # keep existing stored value
        if model is not None:
            setattr(model, modelprop, raw_value)
    return action_item, errors


# ---------------------------------------------------------------------------
# HTML rendering
# ---------------------------------------------------------------------------
CSS = """
/* Colors pulled directly from rocketsoftware.com's own CSS utility classes:
   .bg-bright-blue #503EFF, .bg-purple #990099, .bg-gradient-black #2e2e2e->#000,
   .bg-gray-light #f4f4f4, plus the logo's magenta-to-blue "BLAST" gradient. */
body { font-family: -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 0; background: #f4f4f4; color: #1f2937; }
.app { display: flex; min-height: 100vh; }
.sidebar { width: 260px; background: linear-gradient(180deg, #2e2e2e 0%, #000000 100%); color: #d9d9d9; padding: 20px 0; flex-shrink: 0; }
.sidebar h1 { font-size: 15px; padding: 0 20px 16px; color: #ffffff; border-bottom: 2px solid #503eff; margin: 0 0 12px; }
.sidebar a { display: block; padding: 10px 20px; color: #bdbdbd; text-decoration: none; font-size: 14px; }
.sidebar a.active { background: #503eff; color: #fff; font-weight: 600; }
.sidebar a:hover { background: #1a1a1a; }
.main { flex: 1; padding: 32px 40px; max-width: 860px; }
.page-title { font-size: 20px; margin: 0 0 4px; color: #000; }
.page-sub { color: #6b7280; margin: 0 0 24px; font-size: 13px; }
.card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 24px; }
.field { margin-bottom: 16px; }
.field label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 4px; color: #374151; }
.field input[type=text], .field input[type=password] { width: 100%; max-width: 380px; padding: 8px 10px; border: 1px solid #d1d5db; border-radius: 6px; font-size: 14px; box-sizing: border-box; }
.field input[type=text]:focus, .field input[type=password]:focus { outline: none; border-color: #503eff; box-shadow: 0 0 0 3px rgba(80,62,255,0.15); }
.field input[disabled] { background: #f3f4f6; color: #6b7280; }
.field .hint { color: #9ca3af; font-size: 12px; margin-top: 4px; }
.checkbox-field label { display: inline-flex; align-items: center; gap: 8px; font-weight: 500; }
.static-label { font-size: 14px; color: #374151; margin-bottom: 16px; }
.actions { margin-top: 24px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
button { cursor: pointer; border: none; border-radius: 6px; padding: 9px 18px; font-size: 14px; font-weight: 600; }
.btn-run { background: #503eff; color: #fff; }
.btn-run:hover:not(:disabled) { background: #3f2fd6; }
.btn-run:disabled { background: #b7aeff; cursor: not-allowed; }
.btn-nav { background: #e5e7eb; color: #000; }
.btn-nav:hover:not(:disabled) { background: #d7dbe0; }
.btn-nav.primary { background: #990099; color: #fff; }
.btn-nav.primary:hover:not(:disabled) { background: #7a007a; }
.btn-nav:disabled { background: #f3f4f6; color: #9ca3af; cursor: not-allowed; }
.status { font-size: 13px; font-weight: 600; padding: 4px 10px; border-radius: 999px; }
.status.ok { background: #dcfce7; color: #166534; }
.status.pending { background: #fef9c3; color: #854d0e; }
.status.fail { background: #fbe1df; color: #a3160d; }
.console { background: linear-gradient(90deg, #2e2e2e 0%, #000000 100%); color: #d9f5e5; font-family: Consolas, Menlo, monospace; font-size: 12.5px; padding: 12px; border-radius: 6px; min-height: 90px; max-height: 320px; overflow-y: auto; white-space: pre-wrap; margin-top: 16px; display: block !important; }
.errors { background: #fbe1df; color: #a3160d; border: 1px solid #f3b8b3; border-radius: 6px; padding: 10px 14px; margin-bottom: 16px; font-size: 13px; }
.pager { color: #6b7280; font-size: 12px; margin-bottom: 12px; }
"""

JS = """
function qs(sel) { return document.querySelector(sel); }

function pollJob(jobId, s, p) {
  var offset = 0;
  var consoleEl = qs('#console');
  var runBtn = qs('#run-btn');
  var nextBtn = qs('#next-btn');
  var statusEl = qs('#status');

  function tick() {
    fetch('/api/job/' + jobId + '?offset=' + offset)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.lines && data.lines.length) {
                    consoleEl.textContent += data.lines.join('\\n');
          consoleEl.scrollTop = consoleEl.scrollHeight;
        }
        offset = data.total;
        if (!data.done) {
          setTimeout(tick, 700);
          return;
        }
        runBtn.disabled = false;
        if (data.result) {
          statusEl.className = 'status ok';
          statusEl.textContent = 'Succeeded';
          if (nextBtn) { nextBtn.disabled = false; }
        } else {
          statusEl.className = 'status fail';
          statusEl.textContent = 'Failed - see console output';
        }
      })
      .catch(function () { setTimeout(tick, 1500); });
  }
  tick();
}

function runAction(form, s, p) {
  var runBtn = qs('#run-btn');
  var statusEl = qs('#status');
  runBtn.disabled = true;
  statusEl.className = 'status pending';
  statusEl.textContent = 'Running...';
  qs('#console').textContent = '';

  fetch(form.action, { method: 'POST', body: new URLSearchParams(new FormData(form)) })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.errors && data.errors.length) {
        statusEl.className = 'status fail';
        statusEl.textContent = data.errors.join(' ');
        runBtn.disabled = false;
        return;
      }
      pollJob(data.jobId, s, p);
    });
  return false;
}
"""


def render_page(page_title, body, active_step_idx, steps, error=None):
    sidebar_links = []
    for idx, step in enumerate(steps):
        cls = ' class="active"' if idx == active_step_idx else ''
        sidebar_links.append(
            '<a href="/step/{0}/page/0"{1}>{2}</a>'.format(idx, cls, html.escape(step['name']))
        )

    error_html = ''
    if error:
        error_html = '<div class="errors" style="border: 2px solid red; background: #ffe0e0;"><strong>⚠️ Error:</strong><br>{0}</div>'.format(html.escape(error))

    return """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{css}</style>
<script>{js}</script>
</head>
<body>
<div class="app">
  <div class="sidebar">
    <h1>{wizard_label}</h1>
    {sidebar}
  </div>
  <div class="main">
    {error}
    {body}
  </div>
</div>
</body>
</html>""".format(
        title=html.escape(page_title),
        css=CSS,
        js=JS,
        wizard_label=html.escape(page_title.split(' - ')[0]),
        sidebar=''.join(sidebar_links),
        error=error_html,
        body=body,
    )


def render_field(item, model):
    itype = item['type']
    label = html.escape(item.get('label', '').strip())

    if itype == 'label':
        return '<div class="static-label">{0}</div>'.format(label)

    if itype == 'dummy':
        return ''

    if itype == 'checkbox':
        checked = field_current_value(model, item)
        modelprop = html.escape(item.get('modelprop', ''))
        checked_attr = 'checked' if checked else ''
        return (
            '<div class="field checkbox-field">'
            '<label><input type="checkbox" name="{prop}" {checked}> {label}</label>'
            '</div>'
        ).format(prop=modelprop, checked=checked_attr, label=label)

    if itype in ('editbox', 'password'):
        modelprop = html.escape(item.get('modelprop', ''))
        editable = item.get('editable', True) is not False
        maxlen = item.get('maxlen', 100)
        placeholder = html.escape(str(item.get('placeholder', '')))

        if itype == 'password':
            _, has_value = field_current_value(model, item)
            if has_value and not placeholder:
                placeholder = 'Already set - leave blank to keep'
            value_attr = ''
        else:
            value = field_current_value(model, item)
            value_attr = 'value="{0}"'.format(html.escape(str(value)))

        input_type = 'password' if itype == 'password' else 'text'
        disabled = '' if editable else 'disabled'
        return (
            '<div class="field">'
            '<label>{label}</label>'
            '<input type="{itype}" name="{prop}" maxlength="{maxlen}" {value} placeholder="{ph}" {disabled}>'
            '</div>'
        ).format(label=label, itype=input_type, prop=modelprop, maxlen=maxlen, value=value_attr,
                  ph=placeholder, disabled=disabled)

    return ''


def render_step_page(wizard, s, p, error=None):
    step, page = wizard.step_page(s, p)
    try:
        model = get_model_instance(step)
    except ModelLoadError as exc:
        model = None
        error = error or str(exc)
    state = get_page_state(s, p)

    fields_html = []
    action_item = None
    for item in page['items']:
        if item['type'] == 'button':
            action_item = item
            continue
        fields_html.append(render_field(item, model))

    total_pages = len(step['pages'])
    pager = '<div class="pager">Step {0} of {1} &middot; Page {2} of {3}</div>'.format(
        s + 1, len(wizard.steps), p + 1, total_pages
    )

    lines, _total = state['output'].snapshot()
    console_text = html.escape(''.join(lines)) if lines else '(Console output will appear here...)'

    unlocked = state['unlocked']
    status_class = 'ok' if unlocked else 'pending'
    status_text = 'Succeeded' if unlocked else 'Not run yet'

    run_label = html.escape(action_item['label'].strip()) if action_item else ''
    next_label = html.escape(action_item.get('nextlabel', 'Next').strip()) if action_item else 'Next'

    has_prev = not (s == 0 and p == 0)
    is_last_page_overall = (s == len(wizard.steps) - 1) and (p == total_pages - 1)

    run_section = ''
    if action_item:
        run_section = """
<form id="run-form" action="/step/{s}/page/{p}/run" method="post" onsubmit="return runAction(this, {s}, {p});">
  {fields}
  <div class="actions">
    <button type="submit" id="run-btn" class="btn-run">{run_label}</button>
    <span id="status" class="status {status_class}">{status_text}</span>
  </div>
</form>
<div id="console" class="console">{console}</div>
""".format(s=s, p=p, fields=''.join(fields_html), run_label=run_label,
           status_class=status_class, status_text=status_text, console=console_text)
    else:
        run_section = '<form>{0}</form>'.format(''.join(fields_html))

    nav_section = """
<form action="/step/{s}/page/{p}/nav" method="post">
  <input type="hidden" name="dir" id="nav-dir" value="">
  <div class="actions">
    <button type="submit" class="btn-nav" onclick="document.getElementById('nav-dir').value='prev';" {prev_disabled}>&larr; Previous</button>
    <button type="submit" id="next-btn" class="btn-nav primary" onclick="document.getElementById('nav-dir').value='next';" {next_disabled}>{next_label}{finish}</button>
  </div>
</form>
""".format(
        s=s, p=p,
        prev_disabled='' if has_prev else 'disabled',
        next_disabled='' if unlocked else 'disabled',
        next_label=next_label,
        finish=' \u2192 Done' if is_last_page_overall else '',
    )

    body = """
<div class="page-title">{step_name}</div>
<div class="page-sub">{page_name}</div>
{pager}
<div class="card">
  {run_section}
  {nav_section}
</div>
""".format(step_name=html.escape(step['name']), page_name=html.escape(page['name']),
           pager=pager, run_section=run_section, nav_section=nav_section)

    title = '{0} - {1}'.format(wizard.label, step['name'])
    return render_page(title, body, s, wizard.steps, error=error)


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
def next_position(wizard, s, p):
    step = wizard.steps[s]
    if p + 1 < len(step['pages']):
        return s, p + 1, False
    if s + 1 < len(wizard.steps):
        return s + 1, 0, False
    return s, p, True


def prev_position(wizard, s, p):
    if p > 0:
        return s, p - 1
    if s > 0:
        return s - 1, len(wizard.steps[s - 1]['pages']) - 1
    return s, p


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------
STEP_PAGE_RE = re.compile(r'^/step/(\d+)/page/(\d+)(/(run|nav))?$')


class Handler(BaseHTTPRequestHandler):
    wizard = None  # set by main()

    def log_message(self, fmt, *args):
        logging.info('%s - %s', self.address_string(), fmt % args)

    def _send_html(self, body, status=200):
        payload = body.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, obj, status=200):
        payload = json.dumps(obj).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _redirect(self, location):
        self.send_response(303)
        self.send_header('Location', location)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _read_form(self):
        length = int(self.headers.get('Content-Length', 0) or 0)
        raw = self.rfile.read(length).decode('utf-8') if length else ''
        return parse_qs(raw, keep_blank_values=True)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/favicon.ico':
            self.send_response(204)  # No Content
            self.end_headers()
            return
        
        if parsed.path == '/':
            self._redirect('/step/0/page/0')
            return

        if parsed.path.startswith('/api/job/'):
            job_id = parsed.path[len('/api/job/'):]
            with jobs_lock:
                job = jobs.get(job_id)
            if job is None:
                self._send_json({'error': 'unknown job'}, status=404)
                return
            offset = int(parse_qs(parsed.query).get('offset', ['0'])[0])
            lines, total = job.output.snapshot(offset)
            self._send_json({'lines': lines, 'total': total, 'done': job.done, 'result': job.result})
            return

        m = STEP_PAGE_RE.match(parsed.path)
        if m and not m.group(3):
            s, p = int(m.group(1)), int(m.group(2))
            try:
                html_body = render_step_page(self.wizard, s, p)
            except IndexError:
                self._send_html('<h1>404 - unknown step/page</h1>', status=404)
                return
            self._send_html(html_body)
            return

        self._send_html('<h1>404</h1>', status=404)

    def do_POST(self):
        parsed = urlparse(self.path)
        m = STEP_PAGE_RE.match(parsed.path)
        if not m:
            self._send_html('<h1>404</h1>', status=404)
            return

        s, p = int(m.group(1)), int(m.group(2))
        action = m.group(4)
        form = self._read_form()

        try:
            step, page = self.wizard.step_page(s, p)
        except IndexError:
            self._send_html('<h1>404 - unknown step/page</h1>', status=404)
            return

        try:
            model = get_model_instance(step)
        except ModelLoadError as exc:
            if action == 'run':
                self._send_json({'errors': [str(exc)]})
            else:
                self._redirect('/step/{0}/page/{1}'.format(s, p))
            return

        if action == 'run':
            action_item, errors = apply_form_to_model(model, page['items'], form)
            if errors or action_item is None:
                self._send_json({'errors': errors or ['No action available on this page']})
                return

            state = get_page_state(s, p)
            state['output'] = WebOutputWindow()
            if model is not None:
                model.outputWindow = state['output']

            param = None
            if 'paramClass' in action_item and hasattr(func_param, action_item['paramClass']):
                param = getattr(func_param, action_item['paramClass'])(model)

            func = getattr(model, action_item['modelfunc'])
            job = Job(func, param)
            job.output = state['output']
            with jobs_lock:
                jobs[job.id] = job
            state['job'] = job

            def on_done_wrapper(j=job, st=state):
                j._thread.join()
                st['unlocked'] = bool(j.result)

            job.start()
            threading.Thread(target=on_done_wrapper, daemon=True).start()
            self._send_json({'jobId': job.id})
            return

        if action == 'nav':
            apply_form_to_model(model, page['items'], form)
            direction = form.get('dir', [''])[0]
            if direction == 'prev':
                ns, np_ = prev_position(self.wizard, s, p)
                self._redirect('/step/{0}/page/{1}'.format(ns, np_))
                return
            if direction == 'next':
                state = get_page_state(s, p)
                if not state['unlocked']:
                    self._redirect('/step/{0}/page/{1}'.format(s, p))
                    return
                ns, np_, finished = next_position(self.wizard, s, p)
                if finished:
                    self._send_html(render_page(
                        '{0} - Complete'.format(self.wizard.label),
                        '<div class="page-title">All steps complete</div>'
                        '<div class="card">The installer wizard has finished. You can close this window.</div>',
                        s, self.wizard.steps,
                    ))
                    return
                self._redirect('/step/{0}/page/{1}'.format(ns, np_))
                return

        self._send_html('<h1>400 - bad request</h1>', status=400)


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', nargs='?', choices=['install', 'upgrade'], default='install')
    parser.add_argument('--host', default='127.0.0.1', help='bind address (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8090)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    icwconfig.mode = icwconfig.EModetype.install if args.mode == 'install' else icwconfig.EModetype.upgrade
    icwconfig.prodtype = icwconfig.EProdtype.debug if args.debug else icwconfig.EProdtype.prod

    if os.environ.get('PATH', '').find('/QOpenSys/pkgs/bin') < 0 and os.name != 'nt':
        os.environ['PATH'] = '/QOpenSys/pkgs/bin:' + os.environ.get('PATH', '')

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

    Handler.wizard = Wizard(args.mode)

    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print('iCluster-web {0} wizard running at http://{1}:{2}/'.format(args.mode, args.host, args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
