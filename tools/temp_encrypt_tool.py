from config.config import encrypt

key_to_crypt = input("ENTER YOUR KEY : ")
print(f"Here is your new key : {encrypt(key_to_crypt).decode()}")
