import json
import os
from datetime import datetime

INGESTED_DOCUMENTS_JSON = "ingested_documents.json"

class DocumentTracker:
    def __init__(self, tracker_file=("%s" % INGESTED_DOCUMENTS_JSON)):
        self.tracker_file = tracker_file
        self.documents = self._load_tracker()

    def _load_tracker(self):
        if os.path.exists(self.tracker_file):
            try:
                with open(self.tracker_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def _save_tracker(self):
        with open(self.tracker_file, 'w') as f:
            json.dump(self.documents, f, indent=2)

    def is_document_ingested(self, file_path):
        """Check if document has been ingested based on path and modification time"""
        abs_path = os.path.abspath(file_path)

        # Check if file exists and get its modification time
        if not os.path.exists(abs_path):
            return False

        mod_time = os.path.getmtime(abs_path)

        # Check if document is in tracker and if it has been modified since ingestion
        if abs_path in self.documents:
            return mod_time <= self.documents[abs_path].get("last_modified", 0)

        return False

    def mark_document_ingested(self, file_path):
        """Mark document as ingested with current timestamp"""
        abs_path = os.path.abspath(file_path)

        self.documents[abs_path] = {
            "ingestion_time": datetime.now().isoformat(),
            "last_modified": os.path.getmtime(abs_path)
        }

        self._save_tracker()