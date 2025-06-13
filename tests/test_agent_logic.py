import unittest
import json
import requests
from unittest.mock import patch, MagicMock

from src.medical_assistant.agent import augment_prompt_with_rag, serper_search

class TestAgentLogic(unittest.TestCase):
    """Tests for agent helper functions."""

    def test_augment_prompt_with_rag(self):
        """Test that the RAG context is correctly formatted."""
        mock_vectorstore = MagicMock()
        mock_doc1 = MagicMock()
        mock_doc1.page_content = "Content of doc 1."
        mock_doc2 = MagicMock()
        mock_doc2.page_content = "Content of doc 2."
        
        mock_vectorstore.similarity_search.return_value = [mock_doc1, mock_doc2]

        result = augment_prompt_with_rag("test query", mock_vectorstore)
        
        expected_context = "Content of doc 1.\n----------------\nContent of doc 2."
        self.assertEqual(result, expected_context)
        mock_vectorstore.similarity_search.assert_called_once_with("test query", k=5)

    def test_augment_prompt_with_no_results(self):
        """Test RAG augmentation when the vector store returns no results."""
        mock_vectorstore = MagicMock()
        mock_vectorstore.similarity_search.return_value = []

        result = augment_prompt_with_rag("test query", mock_vectorstore)
        
        self.assertEqual(result, "There was no Local Context")


    @patch('src.medical_assistant.agent.requests.post')
    def test_serper_search_failure(self, mock_post):
        """Test the serper_search function when the API call fails."""
        mock_post.side_effect = requests.exceptions.RequestException("Network Error")

        result = serper_search("flu symptoms", "fake_api_key")

        self.assertEqual(result, "There was no Search Context due to an error.")