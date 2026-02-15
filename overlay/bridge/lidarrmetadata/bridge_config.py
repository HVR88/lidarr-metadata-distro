from lidarrmetadata.config import DefaultConfig, ConfigMeta
import copy
import six

class BridgeConfig(six.with_metaclass(ConfigMeta, DefaultConfig)):
    # Use your mirror's default credentials unless environment overrides exist
    PROVIDERS = {
        'MUSICBRAINZDBPROVIDER': ([], {
            'DB_HOST': 'db',
            'DB_PORT': 5432,
            'DB_USER': 'musicbrainz',
            'DB_PASSWORD': 'musicbrainz',
        }),
        'SOLRSEARCHPROVIDER': ([], {
            'SEARCH_SERVER': 'http://search:8983/solr',
        }),
        'FANARTTVPROVIDER': ([DefaultConfig.FANART_KEY], {}),
        'THEAUDIODBPROVIDER': ([DefaultConfig.TADB_KEY], {}),
        'WIKIPEDIAPROVIDER': ([], {}),
        'SPOTIFYAUTHPROVIDER': ([], {
            'CLIENT_ID': DefaultConfig.SPOTIFY_ID,
            'CLIENT_SECRET': DefaultConfig.SPOTIFY_SECRET,
            'REDIRECT_URI': DefaultConfig.SPOTIFY_REDIRECT_URL
        }),
        'SPOTIFYPROVIDER': ([], {
            'CLIENT_ID': DefaultConfig.SPOTIFY_ID,
            'CLIENT_SECRET': DefaultConfig.SPOTIFY_SECRET
        }),
    }

    USE_CACHE = True
    ENABLE_STATS = False

    # Ensure cache config supports user/password/db_name overrides
    CACHE_CONFIG = copy.deepcopy(DefaultConfig.CACHE_CONFIG)
    for _key in ('fanart', 'tadb', 'wikipedia', 'artist', 'album', 'spotify'):
        if _key in CACHE_CONFIG:
            CACHE_CONFIG[_key].setdefault('user', 'abc')
            CACHE_CONFIG[_key].setdefault('password', 'abc')
            CACHE_CONFIG[_key].setdefault('db_name', 'lm_cache_db')
