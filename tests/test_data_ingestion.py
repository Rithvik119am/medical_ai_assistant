import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock, ANY

import pandas as pd

from src.medical_assistant import data_ingestion
from src.medical_assistant.config import DATA_PATH, PERSIST_DIR, EMBEDDING_MODEL_NAME

class TestDataIngestion(unittest.TestCase):
    """Tests for the data_ingestion.ingest_main function."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.excel_path = os.path.join(self.temp_dir, "test_data.xlsx")
        df = pd.DataFrame({"Sentence": ["foo", "bar", "foo", None]})
        df.to_excel(self.excel_path, index=False)

        self.patcher_data = patch.object(data_ingestion, 'DATA_PATH', self.excel_path)
        self.patcher_persist = patch.object(data_ingestion, 'PERSIST_DIR', os.path.join(self.temp_dir, "db"))
        self.mock_data = self.patcher_data.start()
        self.mock_persist = self.patcher_persist.start()

        self.mock_chroma = MagicMock()
        self.mock_hf = MagicMock()
        self.p_chroma = patch('src.medical_assistant.data_ingestion.Chroma', self.mock_chroma)
        self.p_hf = patch('src.medical_assistant.data_ingestion.HuggingFaceEmbeddings', self.mock_hf)
        self.p_chroma.start()
        self.p_hf.start()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
        patch.stopall()

    def test_ingest_creates_new_db(self):
        with patch('os.path.exists', return_value=False):
            mock_store = MagicMock()
            self.mock_chroma.from_documents.return_value = mock_store

            data_ingestion.ingest_main()

            self.mock_hf.assert_called_once_with(model_name=EMBEDDING_MODEL_NAME)
            self.mock_chroma.from_documents.assert_called_once()
            docs = self.mock_chroma.from_documents.call_args[1]['documents']
            self.assertEqual(len(docs), 3)
            self.assertTrue(all(hasattr(d, 'page_content') for d in docs))

    def test_ingest_adds_new_documents_to_existing_db(self):
        with patch('os.path.exists', return_value=True), patch('os.listdir', return_value=['chroma-xyz']):
            fake_db = MagicMock()
            fake_db.similarity_search.side_effect = [
                [MagicMock(page_content='foo')],
                [],
                [MagicMock(page_content='foo')]
            ]
            self.mock_chroma.return_value = fake_db

            data_ingestion.ingest_main()

            self.mock_chroma.assert_called_with(persist_directory=ANY, embedding_function=ANY)
            self.assertEqual(fake_db.similarity_search.call_count, 3)
            fake_db.add_documents.assert_called_once()
            added = fake_db.add_documents.call_args[1]['documents']
            self.assertEqual(len(added), 1)
            self.assertEqual(added[0].page_content, 'bar')

    def test_ingest_raises_file_not_found(self):
        with patch.object(data_ingestion, 'DATA_PATH', os.path.join(self.temp_dir, 'missing.xlsx')):
            with self.assertRaises(FileNotFoundError):
                data_ingestion.ingest_main()

if __name__ == '__main__':
    unittest.main()
