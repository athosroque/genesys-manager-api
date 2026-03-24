from passlib.context import CryptContext
import sys

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Gera hash seguro bcrypt para a senha."""
    return pwd_context.hash(password)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = input("Digite a senha para gerar o hash: ")
    
    print("\nO seu hash de segurança bcrypt é:")
    print("-----------------------------------")
    print(hash_password(password))
    print("-----------------------------------")
    print("Copie este valor e insira no campo 'hashed_password' de users.json")
