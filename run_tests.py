import unittest
import sys
import os

def run_all_tests():
    """
    Discovers and runs all tests in the /tests directory.
    """
    # Add the project root to the Python path to allow imports like 'from src.module...'
    project_root = os.path.abspath(os.path.dirname(__file__))
    sys.path.insert(0, project_root)

    print("Starting test discovery in 'tests/' directory...")
    loader = unittest.TestLoader()
    suite = loader.discover('tests')
    
    print("Running test suite...")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    if result.wasSuccessful():
        print("All tests passed successfully!")
        sys.exit(0)
    else:
        print("Some tests failed.")
        sys.exit(1)

if __name__ == '__main__':
    run_all_tests()