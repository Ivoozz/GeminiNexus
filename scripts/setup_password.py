from passlib.context import CryptContext
import getpass

# Setup the hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def generate_hash():
    print("--- GeminiNexus Password Hasher ---")
    password = getpass.getpass("Voer het gewenste wachtwoord in: ")
    confirm = getpass.getpass("Bevestig het wachtwoord: ")
    
    if password != confirm:
        print("Fout: Wachtwoorden komen niet overeen!")
        return

    hashed = pwd_context.hash(password)
    print("\n✅ Veilig gehasht wachtwoord gegenereerd:")
    print(f"PASSWORD_HASH={hashed}")
    print("\nKopieer de bovenstaande regel naar je .env bestand.")

if __name__ == "__main__":
    generate_hash()
