import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace
class MockQThread:
    def __init__(self): pass
    def start(self): pass

class MockSignal:
    def __init__(self): self.emitted_value = None
    def emit(self, *args): self.emitted_value = args
    def connect(self, slot): pass

mock_qt_classes = {
    'PySide6.QtCore.QThread': MockQThread,
    'PySide6.QtCore.Signal': MockSignal,
}

with patch.dict('sys.modules', mock_qt_classes):
    from src.medical_assistant.workers import AgentInitializationWorker, MedicalAgentWorker

class TestWorkers(unittest.TestCase):
    """Tests the core logic of the background workers."""

    @patch('src.medical_assistant.workers.create_medical_agent')
    def test_agent_initialization_worker_success(self, mock_create_agent):
        """Test the AgentInitializationWorker's success path."""
        mock_agent = MagicMock()
        mock_store = MagicMock()
        mock_create_agent.return_value = (mock_agent, mock_store)

        worker = AgentInitializationWorker("fake_api_key")
        worker.agent_initialized = MockSignal() 
        
        worker.run() 

        mock_create_agent.assert_called_once_with("fake_api_key")
        self.assertEqual(worker.agent_initialized.emitted_value, (True, mock_agent, mock_store))

    @patch('src.medical_assistant.workers.create_medical_agent')
    def test_agent_initialization_worker_failure(self, mock_create_agent):
        """Test the AgentInitializationWorker's failure path."""
        mock_create_agent.side_effect = Exception("Initialization failed")

        worker = AgentInitializationWorker("fake_api_key")
        worker.agent_initialized = MockSignal()

        worker.run()

        self.assertEqual(worker.agent_initialized.emitted_value, (False, None, None))
    
    @patch('src.medical_assistant.workers.augment_prompt_with_rag')
    def test_medical_agent_worker(self, mock_augment):
        """Test the MedicalAgentWorker's main logic."""
        mock_augment.return_value = "Mocked local context."
        
        mock_agent_executor = MagicMock()
        mock_agent_executor.invoke.return_value = {"messages": [SimpleNamespace(content="This is the AI response.")]}
        
        mock_vector_store = MagicMock()
        
        worker = MedicalAgentWorker(
            agent_executor=mock_agent_executor,
            vector_store=mock_vector_store,
            serper_apiKeyInput="fake_api_key",
            query="test query",
            chat_history=[]
        )
        worker.response_generated = MockSignal()
        
        worker.run()

        mock_augment.assert_called_once_with("test query", mock_vector_store)
        mock_agent_executor.invoke.assert_called_once()
        
        final_response = worker.response_generated.emitted_value[0]
        self.assertIn("This is the AI response.", final_response)
        self.assertIn("⚠️ This information is for educational purposes only", final_response)