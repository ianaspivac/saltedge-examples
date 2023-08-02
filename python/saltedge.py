import requests
import base64
import time

from cryptography.exceptions                   import InvalidSignature
from cryptography.hazmat.primitives            import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends              import default_backend

class SaltEdge:
    digest = "sha256"

    @classmethod
    def verify(cls, path_to_public_key, message, signature):
        """
        Verifies the signature on a message.
        :param path_to_public_key: string, Absolute or relative path to Spectre public key
        :param message: string, The message to verify.
        :param signature: string, The signature on the message.
        :return:
        """
        with open(path_to_public_key, "rb") as public_key_data:
            public_key = serialization.load_pem_public_key(
                public_key_data.read(), backend=default_backend()
            )

        try:
            public_key.verify(
                base64.b64decode(signature),
                bytes(message.encode("utf8")),
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True

        except InvalidSignature:
            return False

    def __init__(self, app_id, secret, private_path):
        self.app_id = app_id
        self.secret = secret

        with open(private_path, "rb") as private_key:
            self._private_key = serialization.load_pem_private_key(
                private_key.read(), password=None, backend=default_backend()
            )

    def sign(self, message):
        """
        Signs a message.
        :param message: string, Message to be signed.
        :return: string, The signature of the message for the given key.
          """
        return base64.b64encode(
            self._private_key.sign(
                bytes(message.encode("utf8")), padding.PKCS1v15(), hashes.SHA256()
            )
        )

    def generate_signature(self, method, expire, url, payload=""):
        """
        Generates base64 encoded SHA256 signature of the string given params, signed with the client's private key.
        :param method: uppercase method of the HTTP request. Example: GET, POST, PATCH, PUT, DELETE, etc.;
        :param expire: request expiration time as a UNIX timestamp in UTC timezone. Recommended value is 1 minute from now. The maximum value is 1 hour from now.
        :param url: the full requested URL, with all its complementary parameters;
        :param payload: the request post body. Should be left empty if it is a GET request, or the body is empty;
        :return: base64 encoded SHA1 signature
        """
        message = "{expire}|{method}|{url}|{payload}".format(**locals())
        return self.sign(message)

    def generate_headers(self, expire):
        return {
            "Accept":       "application/json",
            "Content-type": "application/json",
            "Expires-at":   expire,
            "App-id":       self.app_id,
            "Secret":       self.secret,
        }

    def expires_at(self):
        return str(time.time() + 60)

    def request(self, method, url, payload=""):
        expire               = self.expires_at()
        headers              = self.generate_headers(expire)
        headers["Signature"] = self.generate_signature(
            method.upper(), expire, url, payload
        )

        make_request = getattr(requests, method.lower())

        if method.upper() == "GET":
            return make_request(url, headers=headers)

        return make_request(url, data=payload, headers=headers)
