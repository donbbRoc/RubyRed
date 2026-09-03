require 'rake'
require 'rake/testtask'

# Define a Rake task for running tests
Rake::TestTask.new do |t|
  t.libs << 'test'
  t.pattern = 'test/**/*_test.rb'
end

# Define a task for running all tests
task :test => :test

# Define a default task
task :default => :test

# You can add more tasks here as needed
# For example, a task for building the project or cleaning up files