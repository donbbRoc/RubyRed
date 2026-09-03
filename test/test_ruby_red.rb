require 'minitest/autorun'
require_relative '../lib/ruby_red'

class TestRubyRed < Minitest::Test
  def setup
    @ruby_red = RubyRed.new
  end

  def test_example_functionality
    assert_equal 'RubyRed works!', @ruby_red.example_function
  end
end