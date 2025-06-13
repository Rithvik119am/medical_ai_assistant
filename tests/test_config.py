import unittest

class TestConfig(unittest.TestCase):
    """Tests for the configuration file."""

    def test_config_variables_exist(self):
        """
        Test that essential configuration variables can be imported.
        """
        try:
            from src.medical_assistant.config import (
                PERSIST_DIR,
                EMBEDDING_MODEL_NAME,
                LLM_MODEL_NAME,
                DATA_PATH,
                disclaimer,
                system_prompt,
            )
            self.assertIsNotNone(PERSIST_DIR)
            self.assertIsNotNone(EMBEDDING_MODEL_NAME)
            self.assertIsNotNone(LLM_MODEL_NAME)
            self.assertIsNotNone(DATA_PATH)
            self.assertIsNotNone(disclaimer)
            self.assertIsInstance(system_prompt, str)
            self.assertIn("Triage", system_prompt)

        except ImportError as e:
            self.fail(f"Failed to import from config.py: {e}")

if __name__ == '__main__':
    unittest.main()