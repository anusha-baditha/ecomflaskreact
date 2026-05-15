from itsdangerous import URLSafeTimedSerializer
secret_key=b'u\x83\x83(\x8a'
def endata(data):
    serializer=URLSafeTimedSerializer(secret_key)
    return serializer.dumps(data)
def dndata(data):
    serializer=URLSafeTimedSerializer(secret_key)
    return serializer.loads(data)
