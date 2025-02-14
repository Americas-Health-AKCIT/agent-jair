"""
Essa classe deve ser isolada do resto do código, não importe ela pois não foi testado
"""

from enum import Enum
from typing import Optional, Dict, Union
import boto3
from botocore.exceptions import ClientError
import utils.auth_functions as auth_functions
from firebase_admin import auth 
import json
from botocore.exceptions import ClientError

# Firebase Admin is already initialized in firebase_admin_init.py

class OperationTarget(Enum):
    FIREBASE = "firebase"
    AWS = "aws"
    BOTH = "both"

class UserManagement:
    def __init__(self):
        self.s3 = boto3.client('s3')
        self.BUCKET = "amh-model-dataset"
        self.AUDITORS_KEY = "user_data_app/auditors/auditors.json"
        self.REQUISITIONS_PREFIX = "user_data_app/requisitions"


    def _load_aws_auditors(self) -> Dict:
        """Load auditors data from AWS S3"""
        try:
            response = self.s3.get_object(Bucket=self.BUCKET, Key=self.AUDITORS_KEY)
            return json.loads(response['Body'].read().decode('utf-8'))
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return {"auditors": []}
            raise


    def _save_aws_auditors(self, auditors_data: Dict) -> None:
        """Save auditors data to AWS S3"""
        self.s3.put_object(
            Bucket=self.BUCKET,
            Key=self.AUDITORS_KEY,
            Body=json.dumps(auditors_data, ensure_ascii=False, indent=2).encode('utf-8'),
            ContentType='application/json'
        )


    def get_user_info(self, email: str) -> Dict[str, Union[Dict, None, str]]:
        """Get user information from both Firebase and AWS"""
        result = {
            "firebase_info": None,
            "aws_info": None,
            "status": "success"
        }

        # Get Firebase info using Admin SDK
        try:
            firebase_user = auth.get_user_by_email(email)
            result["firebase_info"] = {
                "uid": firebase_user.uid,
                "email": firebase_user.email,
                "email_verified": firebase_user.email_verified,
                "disabled": firebase_user.disabled,
                "custom_claims": firebase_user.custom_claims
            }
        except auth.UserNotFoundError:
            result["status"] = f"Firebase: User with email {email} not found"
        except Exception as e:
            result["status"] = f"Firebase error: {str(e)}"

        # Get AWS info
        try:
            aws_data = self._load_aws_auditors()
            aws_user = next((a for a in aws_data.get('auditors', []) if a['email'] == email), None)
            result["aws_info"] = aws_user
        except Exception as e:
            if result["status"] == "success":
                result["status"] = f"AWS error: {str(e)}"
            else:
                result["status"] += f" | AWS error: {str(e)}"

        return result


    def add_user(self, email: str, password: str, name: str, role: str = "auditor", 
                target: OperationTarget = OperationTarget.BOTH) -> Dict[str, str]:
        """Add user to specified targets (Firebase, AWS, or both)"""
        result = {
            "status": "success",
            "message": "",
            "firebase_uid": None
        }

        if role not in auth_functions.VALID_ROLES:
            return {
                "status": "error",
                "message": f"Role inválida. Deve ser um dos seguintes: {', '.join(auth_functions.VALID_ROLES)}"
            }

        # Firebase Creation
        if target in [OperationTarget.FIREBASE, OperationTarget.BOTH]:
            try:
                firebase_user = auth.create_user(
                    email=email,
                    password=password
                )
                auth.set_custom_user_claims(firebase_user.uid, {'role': role})
                result["firebase_uid"] = firebase_user.uid
                result["message"] += "Firebase: Usuário criado com sucesso. "
            except auth.EmailAlreadyExistsError:
                result["status"] = "error"
                result["message"] += "Firebase: Email já cadastrado. "
            except Exception as e:
                result["status"] = "error"
                result["message"] += f"Firebase error: {str(e)}. "
                return result

        # AWS Creation
        if target in [OperationTarget.AWS, OperationTarget.BOTH]:
            try:
                aws_data = self._load_aws_auditors()
                
                if any(a['email'] == email for a in aws_data.get('auditors', [])):
                    if result["firebase_uid"] and target == OperationTarget.BOTH:
                        # Rollback Firebase creation if AWS fails in BOTH mode
                        try:
                            auth.delete_user(result["firebase_uid"])
                            result["message"] += "Firebase: Usuário deletado após falha no AWS. "
                        except:
                            result["message"] += "Firebase: Erro ao deletar usuário após falha no AWS. "
                    
                    result["status"] = "error"
                    result["message"] += "AWS: Email já existe. "
                    return result

                existing_ids = [int(a['id']) for a in aws_data.get('auditors', [])]
                new_id = str(max(existing_ids + [0]) + 1)
                
                new_auditor = {
                    'id': new_id,
                    'name': name,
                    'email': email,
                    'role': role
                }
                
                if 'auditors' not in aws_data:
                    aws_data['auditors'] = []
                
                aws_data['auditors'].append(new_auditor)
                self._save_aws_auditors(aws_data)
                result["message"] += "AWS: Usuário criado com sucesso. "
                
            except Exception as e:
                if result["firebase_uid"] and target == OperationTarget.BOTH:
                    # Rollback Firebase creation if AWS fails in BOTH mode
                    try:
                        auth.delete_user(result["firebase_uid"])
                        result["message"] += "Firebase: Usuário deletado após falha no AWS. "
                    except:
                        result["message"] += "Firebase: Erro ao deletar usuário após falha no AWS. "
                
                result["status"] = "error"
                result["message"] += f"AWS error: {str(e)}. "

        return result


    def delete_user(self, email: str, target: OperationTarget = OperationTarget.BOTH) -> Dict[str, str]:
        """Delete user from specified targets (Firebase, AWS, or both)"""
        result = {"status": "success", "message": ""}

        if target in [OperationTarget.FIREBASE, OperationTarget.BOTH]:
            try:
                # Use existing function to delete from Firebase
                auth_functions.delete_account_adm(email)
                result["message"] += "Firebase: User deleted successfully. "
            except Exception as e:
                result["status"] = "error"
                result["message"] += f"Firebase error: {str(e)}. "

        if target in [OperationTarget.AWS, OperationTarget.BOTH]:
            try:
                aws_data = self._load_aws_auditors()
                auditor = next((a for a in aws_data['auditors'] if a['email'] == email), None)
                
                if auditor:
                    aws_data['auditors'].remove(auditor)
                    self._save_aws_auditors(aws_data)
                    result["message"] += "AWS: User deleted successfully. "
                else:
                    if result["status"] == "success":
                        result["status"] = "error"
                    result["message"] += f"AWS: User with email {email} not found. "
            except Exception as e:
                result["status"] = "error"
                result["message"] += f"AWS error: {str(e)}. "

        return result


    def get_all_users_info(self) -> Dict[str, Union[Dict, None, str]]:
        """Get information for all users from both Firebase and AWS"""
        result = {
            "firebase_users": [],
            "aws_users": [],
            "status": "success",
            "message": ""
        }

        # Get all Firebase users
        try:
            # List all users from Firebase (handle pagination)
            page = auth.list_users()
            while page:
                for user in page.users:
                    user_info = {
                        "uid": user.uid,
                        "email": user.email,
                        "email_verified": user.email_verified,
                        "disabled": user.disabled,
                        "custom_claims": user.custom_claims
                    }
                    result["firebase_users"].append(user_info)

                # Get next page of users
                page = page.get_next_page()

        except Exception as e:
            result["status"] = "error"
            result["message"] += f"Firebase error: {str(e)}. "

        # Get all AWS users
        try:
            aws_data = self._load_aws_auditors()
            result["aws_users"] = aws_data.get('auditors', [])
        except Exception as e:
            result["status"] = "error"
            result["message"] += f"AWS error: {str(e)}"

        return result


    def get_all_items_and_requisitions(self) -> Dict[str, Union[list, str]]:
        """Get all items and requisitions from AWS S3"""
        result = {
            "requisitions": [],
            "items": [],
            "status": "success",
            "message": ""
        }

        try:
            # List all objects in the requisitions directory
            response = self.s3.list_objects_v2(
                Bucket=self.BUCKET, 
                Prefix="user_data_app/requisitions"
            )

            # Process each requisition file
            for obj in response.get('Contents', []):
                if obj['Key'].endswith('.json'):
                    try:
                        # Load requisition data
                        file_response = self.s3.get_object(
                            Bucket=self.BUCKET, 
                            Key=obj['Key']
                        )
                        req_data = json.loads(file_response['Body'].read().decode('utf-8'))
                        result["requisitions"].append(req_data)

                        # Extract items data if available
                        if req_data.get('model_output') and req_data['model_output'].get('items'):
                            req_id = req_data['requisition']['Número da requisição']
                            timestamp = req_data['timestamp'].split('.')[0]  # Remove microseconds
                            auditor = req_data.get('auditor', 'Não informado')

                            for item in req_data['model_output']['items']:
                                item_data = {
                                    'requisicao': req_id,
                                    'data': timestamp,
                                    'auditor': auditor,
                                    'descricao': item['description'],
                                    'codigo': item['Código correspondente ao item'],
                                    'decisao_jair': 'AUTORIZADO' if 'AUTORIZADO' in item.get('Situação', '').upper() else 'NEGADO',
                                    'decisao_auditor': 'AUTORIZADO' if item.get('auditor', {}).get('authorized_item', False) else 'NEGADO',
                                    'avaliacao_qualidade': 'BOA' if item.get('auditor', {}).get('quality_rating', False) else 'RUIM',
                                    'tem_avaliacao': 'auditor' in item and 'authorized_item' in item['auditor']
                                }
                                result["items"].append(item_data)

                    except Exception as e:
                        result["message"] += f"Error processing file {obj['Key']}: {str(e)}. "

        except Exception as e:
            result["status"] = "error"
            result["message"] = f"Error listing objects: {str(e)}"

        return result


    def change_user_role(self, email: str, new_role: str, target: OperationTarget = OperationTarget.BOTH) -> Dict[str, str]:
        """Change user role in specified targets (Firebase, AWS, or both)"""
        result = {
            "status": "success",
            "message": ""
        }

        if new_role not in auth_functions.VALID_ROLES:
            return {
                "status": "error",
                "message": f"Invalid role. Must be one of: {', '.join(auth_functions.VALID_ROLES)}"
            }

        if target in [OperationTarget.FIREBASE, OperationTarget.BOTH]:
            try:
                firebase_user = auth.get_user_by_email(email)
                auth.set_custom_user_claims(firebase_user.uid, {'role': new_role})
                result["message"] += "Firebase: User role updated successfully. "
            except auth.UserNotFoundError:
                result["status"] = "error"
                result["message"] += f"Firebase: User with email {email} not found. "
            except Exception as e:
                result["status"] = "error"
                result["message"] += f"Firebase error: {str(e)}. "

        if target in [OperationTarget.AWS, OperationTarget.BOTH]:
            try:
                aws_data = self._load_aws_auditors()
                auditor = next((a for a in aws_data['auditors'] if a['email'] == email), None)

                if auditor:
                    auditor['role'] = new_role
                    self._save_aws_auditors(aws_data)
                    result["message"] += "AWS: User role updated successfully. "
                else:
                    if result["status"] == "success":
                        result["status"] = "error"
                    result["message"] += f"AWS: User with email {email} not found. "
            except Exception as e:
                result["status"] = "error"
                result["message"] += f"AWS error: {str(e)}. "

        return result

    def delete_requisition(self, requisition_number: str) -> Dict[str, str]:
        """Delete a requisition completely from AWS S3.
        
        Args:
            requisition_number (str): The requisition number to delete
            
        Returns:
            Dict[str, str]: A dictionary containing the status and message of the operation
        """
        result = {
            "status": "success",
            "message": ""
        }
        
        print(f"\n[DEBUG] Starting deletion process for requisition {requisition_number}")
        
        try:
            # First try to delete the specific requisition file
            specific_key = f"{self.REQUISITIONS_PREFIX}/{requisition_number}.json"
            print(f"[DEBUG] Attempting to delete file: {specific_key}")
            
            try:
                self.s3.delete_object(
                    Bucket=self.BUCKET,
                    Key=specific_key
                )
                print(f"[DEBUG] Successfully deleted file: {specific_key}")
                result["message"] += f"Deleted requisition file: {specific_key}. "
                result["status"] = "success"
            except Exception as e:
                print(f"[DEBUG] Error deleting file: {specific_key}")
                print(f"[DEBUG] Error details: {str(e)}")
                result["message"] += f"Error deleting requisition file: {str(e)}. "
                result["status"] = "error"

            # Then try to delete from the requisition_history.json
            try:
                history_key = "user_data_app/requisition_history.json"  # Removed 'requisitions' from path
                print(f"[DEBUG] Attempting to update history file: {history_key}")
                
                try:
                    # Get current requisition_history.json
                    print("[DEBUG] Reading current history file")
                    response = self.s3.get_object(
                        Bucket=self.BUCKET,
                        Key=history_key
                    )
                    history_data = json.loads(response['Body'].read().decode('utf-8'))
                    print(f"[DEBUG] Current history structure: {list(history_data.keys())}")
                    
                    if "requisitions" in history_data:
                        original_length = len(history_data["requisitions"])
                        print(f"[DEBUG] Current history has {original_length} requisitions")
                        print(f"[DEBUG] Looking for requisition {requisition_number} to delete")
                        
                        # Print some sample data for debugging
                        if original_length > 0:
                            print(f"[DEBUG] Sample requisition structure: {history_data['requisitions'][0]}")
                        
                        # Filter out the requisition to delete
                        history_data["requisitions"] = [
                            req for req in history_data["requisitions"]
                            if str(req.get("Número da requisição", "")) != str(requisition_number)
                        ]
                        
                        new_length = len(history_data["requisitions"])
                        print(f"[DEBUG] After filtering: {new_length} requisitions")
                        
                        if new_length < original_length:
                            # Save back the filtered history
                            print("[DEBUG] Saving updated history file")
                            self.s3.put_object(
                                Bucket=self.BUCKET,
                                Key=history_key,
                                Body=json.dumps(history_data, ensure_ascii=False, indent=2).encode('utf-8'),
                                ContentType='application/json'
                            )
                            print("[DEBUG] Successfully saved updated history")
                            result["message"] += "Removed from requisition history. "
                            result["status"] = "success"
                        else:
                            print(f"[DEBUG] Requisition {requisition_number} not found in history")
                            result["message"] += "Requisition not found in history. "
                    else:
                        print("[DEBUG] Invalid history file structure - no 'requisitions' key")
                        result["message"] += "Invalid history file structure. "
                        
                except ClientError as e:
                    if e.response['Error']['Code'] == 'NoSuchKey':
                        print("[DEBUG] History file not found")
                        result["message"] += "Requisition history file not found. "
                    else:
                        print(f"[DEBUG] AWS Client Error: {str(e)}")
                        raise
            except Exception as e:
                print(f"[DEBUG] Error updating history: {str(e)}")
                result["message"] += f"Error updating requisition history: {str(e)}. "
                
        except Exception as e:
            print(f"[DEBUG] Critical error in deletion process: {str(e)}")
            result["status"] = "error"
            result["message"] = f"Error in deletion process: {str(e)}"
        
        print(f"[DEBUG] Deletion process completed. Status: {result['status']}")
        print(f"[DEBUG] Final message: {result['message']}")
            
        return result

def load_auditors(s3, BUCKET, AUDITORS_KEY):
    """Load auditors from S3"""
    try:
        response = s3.get_object(Bucket=BUCKET, Key=AUDITORS_KEY)
        return json.loads(response["Body"].read().decode("utf-8"))
    except ClientError as e:
        if e.response["Error"]["Code"] == "NoSuchKey":
            return {"auditors": []}
        raise

if __name__ == "__main__":
    user_manager = UserManagement()
    
    # Pegar informações de um usuário específico
    # user_info = user_manager.get_user_info("edwardsj1020304050@gmail.com")
    # print(user_info)

    # Pegar informações de todos os usuários
    all_users = user_manager.get_all_users_info()
    print("\nAll Users Information before:")
    print(all_users)

    # Pegar informações de todos os itens e requisições
    print("\nLoading items and requisitions...")
    data = user_manager.get_all_items_and_requisitions()

    print(f"\nTotal requisitions: {len(data['requisitions'])}")
    print(f"Total items: {len(data['items'])}")
    if data['message']:
        print(f"Messages: {data['message']}")


    # result = user_manager.add_user(
    #     email="example@mail.com",
    #     password="****",
    #     name="John Doe",
    #     role="auditor",
    #     target=OperationTarget.BOTH
    # )
    # print(result)

    # result = user_manager.delete_user(
    #     email="admamhceia@gmail.com",
    #     target=OperationTarget.FIREBASE
    # )
    # print(result)

    # print(data)

    all_users = user_manager.get_all_users_info()
    print("\nAll Users Information after:")
    print(all_users)