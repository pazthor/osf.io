# -*- coding: utf-8 -*-

import httplib

import itsdangerous
from flask import request

from framework.auth import Auth
from framework.sessions import Session
from framework.exceptions import HTTPError
from framework.auth.decorators import must_be_logged_in, must_be_signed

from website import settings
from website.models import User, Node, NodeLog
from website.project import decorators
from website.project.decorators import must_be_valid_project


@decorators.must_have_permission('write')
@decorators.must_not_be_registration
def disable_addon(**kwargs):

    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']

    addon_name = kwargs.get('addon')
    if addon_name is None:
        raise HTTPError(httplib.BAD_REQUEST)

    deleted = node.delete_addon(addon_name, auth)

    return {'deleted': deleted}


@must_be_logged_in
def get_addon_user_config(**kwargs):

    user = kwargs['auth'].user

    addon_name = kwargs.get('addon')
    if addon_name is None:
        raise HTTPError(httplib.BAD_REQUEST)

    addon = user.get_addon(addon_name)
    if addon is None:
        raise HTTPError(httplib.BAD_REQUEST)

    return addon.to_json(user)


def check_file_guid(guid):

    guid_url = '/{0}/'.format(guid._id)
    if not request.path.startswith(guid_url):
        url_split = request.url.split(guid.file_url)
        try:
            guid_url += url_split[1].lstrip('/')
        except IndexError:
            pass
        return guid_url
    return None


def get_user_from_cookie(cookie):
    token = itsdangerous.Signer(settings.SECRET_KEY).unsign(cookie)
    session = Session.load(token)
    if session is None:
        return None
    return User.load(session.data['auth_user_id'])


# TODO: Implement me
def check_token(user, token):
    pass


permission_map = {
    'metadata': 'read',
    'download': 'read',
    'upload': 'write',
    'delete': 'write',
    'copy': 'write',
    'move': 'write',
}


def get_auth(**kwargs):
    try:
        action = request.args['action']
        cookie = request.args['cookie']
        token = request.args['token']
        node_id = request.args['nid']
        provider_name = request.args['provider']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    user = get_user_from_cookie(cookie)

    if user is not None:
        auth = {
            'id': user._id,
            'email': '{}@osf.io'.format(user._id),
            'name': user.fullname,
        }
    else:
        auth = {}

    check_token(user, token)

    node = Node.load(node_id)
    if not node:
        raise HTTPError(httplib.NOT_FOUND)

    # TODO: Handle view-only links
    try:
        permission_required = permission_map[action]
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)

    if not node.has_permission(user, permission_required):
        raise HTTPError(httplib.BAD_REQUEST)

    provider_settings = node.get_addon(provider_name)
    if not provider_settings:
        raise HTTPError(httplib.BAD_REQUEST)

    credentials = provider_settings.serialize_waterbutler_credentials()
    settings = provider_settings.serialize_waterbutler_settings()

    return {
        'auth': auth,
        'credentials': credentials,
        'settings': settings,
        'callback_url': node.api_url_for(
            'create_waterbutler_log',
            _absolute=True,
        ),
    }


LOG_ACTION_MAP = {
    'create': NodeLog.FILE_ADDED,
    'update': NodeLog.FILE_UPDATED,
    'delete': NodeLog.FILE_REMOVED,
}


@must_be_signed
@must_be_valid_project
def create_waterbutler_log(payload, **kwargs):
    try:
        auth = payload['auth']
        action = payload['action']
        provider = payload['provider']
        metadata = payload['metadata']
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)
    user = User.load(auth['id'])
    if user is None:
        raise HTTPError(httplib.BAD_REQUEST)
    node = kwargs['node'] or kwargs['project']
    node_addon = node.get_addon(provider)
    if node_addon is None:
        raise HTTPError(httplib.BAD_REQUEST)
    try:
        osf_action = LOG_ACTION_MAP[action]
    except KeyError:
        raise HTTPError(httplib.BAD_REQUEST)
    auth = Auth(user=user)
    node_addon.create_waterbutler_log(auth, osf_action, metadata)