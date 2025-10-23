from typing import Any, Dict, List

import bcrypt
from bson import ObjectId
from pymongo.database import Database


def hash_password(password: str) -> bytes:
    """Gera o hash de uma senha."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())


def check_password(password: str, hashed_password: bytes) -> bool:
    """Verifica se a senha corresponde ao hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)


def find_user_by_username(
    db: Database, username: str
) -> Dict[str, Any] | None:
    """Busca um usuário pelo nome."""
    return db['users'].find_one({'username': username})


def bootstrap_initial_user(db: Database, user_data: Dict[str, str]):
    """Cria o usuário inicial se ele não existir no banco."""
    username = user_data.get('username')
    if username and not find_user_by_username(db, username):
        password = user_data.get('password')
        hashed_pw = hash_password(password)
        db['users'].insert_one(
            {
                'username': username,
                'hashed_password': hashed_pw,
                'role': 'admin-dev',
            }
        )
        print(f"Usuário inicial '{username}' criado com sucesso.")


def get_all_users(db: Database, admin_dev=False) -> List[Dict[str, Any]]:
    """Retorna todos os usuários, exceto senhas. Se admin-dev for False, exclui usuários com essa role."""
    query = {'role': {'$ne': 'admin-dev'}} if not admin_dev else {}
    projection = {'hashed_password': 0}
    return list(db['users'].find(query, projection))


def create_user(db: Database, user_data: Dict[str, Any]):
    """Cria um novo usuário com senha hasheada."""
    password = user_data.pop('password')
    user_data['hashed_password'] = hash_password(password)
    return db['users'].insert_one(user_data)


def update_user(db: Database, user_id: ObjectId, update_data: Dict[str, Any]):
    """Atualiza dados de um usuário. Se a senha for fornecida, faz o hash."""
    if 'username' in update_data:
        existing_user = find_user_by_username(db, update_data['username'])
        if existing_user and existing_user['_id'] != user_id:
            raise ValueError('O nome de usuário já está em uso.')

    if 'password' in update_data:
        password = update_data.pop('password')
        if password:
            update_data['hashed_password'] = hash_password(password)

    return db['users'].update_one({'_id': user_id}, {'$set': update_data})


def delete_user(db: Database, user_id: ObjectId):
    """Deleta um usuário."""
    return db['users'].delete_one({'_id': user_id})

def get_all_enrollments_by_semester(
    db: Database, semester: str
) -> List[Dict[str, Any]]:
    if not semester or semester == 'N/A':
        return []
    return list(db['inscricoes'].find({'semester': semester}))

def delete_enrollment(db: Database, enrollment_id: ObjectId):
    """Deleta uma inscrição com base no seu ObjectId."""
    return db['inscricoes'].delete_one({'_id': enrollment_id}).deleted_count


def get_all_turmas(db: Database) -> List[Dict[str, Any]]:
    return list(db['turma'].find())


def get_unique_semesters(db: Database) -> List[str]:
    return db['turma'].distinct('semester')


def add_turma(db: Database, turma_data: Dict[str, Any]):
    return db['turma'].insert_one(turma_data)


def update_turma(db: Database, turma_id: ObjectId, turma_data: Dict[str, Any]):
    return (
        db['turma']
        .update_one({'_id': turma_id}, {'$set': turma_data})
        .modified_count
    )


def delete_turma(db: Database, turma_id: ObjectId):
    return db['turma'].delete_one({'_id': turma_id}).deleted_count


def get_configuracoes(db: Database) -> Dict[str, Any]:
    config = db['config'].find_one()
    return config if config else {}


def update_configuracoes(db: Database, new_config: Dict[str, Any]):
    return (
        db['config']
        .update_one({}, {'$set': new_config}, upsert=True)
        .acknowledged
    )

