import os


def get_config():
    config = {
        'db_binds': {
            'default': 'default.sqlite',
            'score': 'score.sqlite'
        }
    }
    return config


def _mkdir_if_not_exists_and_return_path(path):
    os.makedirs(path, exist_ok = True)
    return path


def get_root_dir():
    return os.path.split(os.path.realpath(__file__))[0]


def get_plugin_dir(plugin_dir_name):
    return _mkdir_if_not_exists_and_return_path(os.path.join(get_root_dir(), plugin_dir_name))


def get_db_dir():
    return _mkdir_if_not_exists_and_return_path(os.path.join(get_root_dir(), 'data', 'db'))


def get_default_db_path():
    return os.path.join(get_db_dir(), 'default.sqlite')


def get_tmp_dir():
    return _mkdir_if_not_exists_and_return_path(os.path.join(get_root_dir(), 'data', 'tmp'))


def get_env_host():
    return os.environ.get('HOST', '0.0.0.0')


def get_env_port():
    return os.environ.get('PORT', '8080')

