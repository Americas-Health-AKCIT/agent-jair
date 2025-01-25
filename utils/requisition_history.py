import json
import os
from typing import Dict, List, Optional, Union
from datetime import datetime
import pandas as pd
import boto3
from botocore.exceptions import ClientError

class RequisitionHistory:
    def __init__(self):
        self.s3_bucket = "amh-model-dataset"
        self.base_prefix = "user_data_app"
        self.requisitions_prefix = f"{self.base_prefix}/requisitions"
        self.history_key = f"{self.base_prefix}/requisition_history.json"
        self.s3 = boto3.client('s3')
        self.history = self._load_history()

    def _load_history(self) -> Dict:
        """Load history from S3 or create new if doesn't exist"""
        try:
            response = self.s3.get_object(Bucket=self.s3_bucket, Key=self.history_key)
            return json.loads(response['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return {
                    "requisitions": [],
                    "evaluations": {}  # New structure for evaluations
                }
            raise

    def _serialize_data(self, data: Dict) -> Dict:
        """Convert non-serializable types to serializable ones"""
        serialized = {}
        for key, value in data.items():
            if isinstance(value, (pd.Timestamp, datetime)):
                serialized[key] = value.isoformat()
            elif isinstance(value, dict):
                serialized[key] = self._serialize_data(value)
            elif isinstance(value, list):
                serialized[key] = [self._serialize_data(item) if isinstance(item, dict) else item for item in value]
            else:
                serialized[key] = value
        return serialized

    def save_complete_requisition(self, requisition_data: Dict, model_output: Optional[Dict] = None, feedback: Optional[Dict] = None, auditor: Optional[str] = None) -> None:
        """Save a complete requisition with all its associated data"""
        req_id = str(requisition_data['Número da requisição'])
        
        complete_data = {
            "requisition": requisition_data,
            "model_output": model_output,
            "feedback": feedback,
            "auditor": auditor,
            "timestamp": datetime.now().isoformat()
        }
        
        # Serialize the data
        serialized_data = self._serialize_data(complete_data)
        
        # Save individual requisition file to S3
        req_key = f"{self.requisitions_prefix}/{req_id}.json"
        self.s3.put_object(
            Bucket=self.s3_bucket,
            Key=req_key,
            Body=json.dumps(serialized_data, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType='application/json'
        )
        
        # Update main history file
        for idx, req in enumerate(self.history["requisitions"]):
            if "requisition" in req:
                existing_id = str(req["requisition"]['Número da requisição'])
            else:
                existing_id = str(req['Número da requisição'])
            
            if existing_id == req_id:
                self.history["requisitions"][idx] = {
                    "Número da requisição": req_id,
                    "Nome do beneficiário": requisition_data.get("Nome do beneficiário", "N/A"),
                    "timestamp": complete_data["timestamp"],
                    "auditor": auditor
                }
                # Update evaluation if feedback exists
                if feedback:
                    self._save_evaluation(req_id, feedback)
                self._save_to_file()
                return
                
        # If not found, append new summary to history
        self.history["requisitions"].append({
            "Número da requisição": req_id,
            "Nome do beneficiário": requisition_data.get("Nome do beneficiário", "N/A"),
            "timestamp": complete_data["timestamp"],
            "auditor": auditor
        })
        # Save evaluation if feedback exists
        if feedback:
            self._save_evaluation(req_id, feedback)
        self._save_to_file()

    def _save_evaluation(self, req_id: str, feedback: Dict) -> None:
        """Save user evaluation data to history"""
        evaluation = {
            "timestamp": datetime.now().isoformat(),
            "authorized_items": feedback.get('authorized_items', []),
            "explanation_incorrect": feedback.get('explainIncorrect', ''),
            "quality_rating": feedback.get('correctChoiceReview'),
            "comments": feedback.get('comment', ''),
            "justifications": feedback.get('justifications', {})
        }
        
        if "evaluations" not in self.history:
            self.history["evaluations"] = {}
            
        self.history["evaluations"][req_id] = evaluation

    def get_complete_requisition(self, req_id: str) -> Optional[Dict]:
        """Get a complete requisition by ID including model outputs and feedback"""
        req_key = f"{self.requisitions_prefix}/{str(req_id)}.json"
        try:
            response = self.s3.get_object(Bucket=self.s3_bucket, Key=req_key)
            data = json.loads(response['Body'].read().decode('utf-8'))
            # Add evaluation data if exists
            if "evaluations" in self.history and str(req_id) in self.history["evaluations"]:
                data["evaluation"] = self.history["evaluations"][str(req_id)]
            return data
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                # Fallback to old format in history file
                for req in self.history["requisitions"]:
                    if "requisition" not in req:
                        if str(req['Número da requisição']) == str(req_id):
                            return {
                                "requisition": req,
                                "model_output": None,
                                "feedback": None,
                                "timestamp": "Data não disponível"
                            }
            else:
                raise
        return None

    def get_all_requisitions(self) -> List[Dict]:
        """Get all requisitions basic info for display"""
        requisitions = sorted(self.history["requisitions"], key=lambda x: x.get('timestamp', ''), reverse=True)
        # Add evaluation status to each requisition
        for req in requisitions:
            req_id = str(req['Número da requisição'])
            req['has_evaluation'] = req_id in self.history.get("evaluations", {})
        return requisitions

    def has_requisition(self, req_id: str) -> bool:
        """Check if a requisition exists and has complete data"""
        req_key = f"{self.requisitions_prefix}/{str(req_id)}.json"
        try:
            response = self.s3.get_object(Bucket=self.s3_bucket, Key=req_key)
            data = json.loads(response['Body'].read().decode('utf-8'))
            return data.get("model_output") is not None
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return False
            raise

    def _save_to_file(self) -> None:
        """Save history to S3"""
        self.s3.put_object(
            Bucket=self.s3_bucket,
            Key=self.history_key,
            Body=json.dumps(self.history, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType='application/json'
        ) 