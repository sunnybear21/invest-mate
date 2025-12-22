import bcrypt
from src.database import create_user, get_user_by_username

def register_user(username, password):
    """
    Registers a new user using the configured database backend.
    """
    if not username or not password:
        return False, "아이디와 비밀번호를 입력해주세요."
        
    # Hash password
    # bcrypt.hashpw returns bytes
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    # Delegate to DB backend
    return create_user(username, hashed)

def login_user(username, password):
    """
    Logs in a user using the configured database backend.
    """
    # Delegate to DB backend
    user = get_user_by_username(username)
    
    if user:
        p_hash = user['password_hash']
        # Ensure p_hash is bytes for bcrypt
        if isinstance(p_hash, str):
             # If it was stored as string (e.g. latin-1 in GSheets), encode back to bytes
             p_hash = p_hash.encode('latin-1')

        if bcrypt.checkpw(password.encode('utf-8'), p_hash):
            return user
            
    return None
