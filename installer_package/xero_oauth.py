from authlib.integrations.flask_client import OAuth

def init_oauth(app):
    oauth = OAuth(app)
    xero = oauth.register(
        name='xero',
        client_id=app.config['XERO_CLIENT_ID'],
        client_secret=app.config['XERO_CLIENT_SECRET'],

        #  This is the key line that resolves "Missing jwks_uri"
        server_metadata_url='https://identity.xero.com/.well-known/openid-configuration',

        # Optional: still fine to keep explicit endpoints, but not necessary when using server_metadata_url
        # authorize_url='https://login.xero.com/identity/connect/authorize',
        # access_token_url='https://identity.xero.com/connect/token',
        # refresh_token_url='https://identity.xero.com/connect/token',

        client_kwargs={
            'scope': 'offline_access openid profile email accounting.settings accounting.transactions accounting.contacts'
        },
    )
    return oauth, xero
