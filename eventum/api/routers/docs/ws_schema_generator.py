"""Asyncapi schema generator for websocket endpoints."""

from dataclasses import asdict
from itertools import chain
from typing import Annotated, Any, get_args, get_origin

import yaml
from fastapi import FastAPI
from fastapi.dependencies.utils import get_dependant
from pydantic_core import PydanticUndefined
from starlette.routing import WebSocketRoute

import eventum.api.utils.websocket_annotations as ws_info


def generate_asyncapi_schema(  # noqa: C901, PLR0912, PLR0915
    app: FastAPI,
    host: str,
    port: int,
) -> dict[str, Any]:
    """Generate an AsyncAPI schema for all websocket endpoints in
    the provided FastAPI app.

    Parameters
    ----------
    app : FastAPI
        The FastAPI application.

    host : str
        Host of the websocket server.

    port : int
        Port of the websocket server.

    Returns
    -------
    dict[str, Any]
        AsyncAPI schema as a dictionary.

    """
    server_name = 'local'

    asyncapi: dict[str, Any] = {
        'asyncapi': '3.0.0',
        'info': {
            'title': app.title,
            'version': app.version,
            'description': app.description,
            'contact': app.contact,
            'license': app.license_info,
            'tags': app.openapi_tags or [],
            'externalDocs': app.openapi_external_docs,
        },
        'servers': {
            server_name: {
                'host': f'{host}:{port}',
                'protocol': 'ws',
            },
        },
        'channels': {},
        'operations': {},
        'components': {},
    }

    channels: dict[str, Any] = asyncapi['channels']
    operations: dict[str, Any] = asyncapi['operations']
    components: dict[str, Any] = asyncapi['components']
    components['messages'] = {}
    components['securitySchemes'] = {}
    components['securitySchemes']['basicAuth'] = {
        'type': 'userPassword',
        'description': 'Basic authentication with username and password',
    }
    components['securitySchemes']['sessionAuth'] = {
        'type': 'httpApiKey',
        'description': 'Session-based authentication using cookie',
        'in': 'cookie',
        'name': 'session_id',
    }

    for route in app.routes:
        if not isinstance(route, WebSocketRoute):
            continue

        channel_id = route.name
        dependant = get_dependant(path=route.path, call=route.endpoint)

        if dependant.websocket_param_name is None:
            continue

        parameters: dict[str, dict] = {}
        for field in chain(dependant.query_params, dependant.path_params):
            parameter = {'description': field.field_info.description or ''}
            if field.default is not PydanticUndefined:
                parameter['default'] = str(field.default)

            parameters[field.name] = parameter

        websocket_annotations = route.endpoint.__annotations__[
            dependant.websocket_param_name
        ]
        messages: dict[str, Any] = {}
        error_messages: dict[str, Any] = {}
        if get_origin(websocket_annotations) is Annotated:
            _, *metadata = get_args(websocket_annotations)
            for meta in metadata:
                if isinstance(meta, ws_info.Receives | ws_info.Sends):
                    if isinstance(meta, ws_info.Receives):
                        action = 'receive'
                    else:
                        action = 'send'

                    message_id = f'{channel_id}_{meta.message.name}'

                    message = asdict(meta.message)
                    if not meta.message.externalDocs:
                        del message['externalDocs']
                    if not meta.message.correlationId:
                        del message['correlationId']
                    if not meta.message.headers:
                        del message['headers']

                    components['messages'][message_id] = message
                    messages[message_id] = {
                        '$ref': f'#/components/messages/{message_id}',
                    }

                    operation_id = f'{message_id}_{action}'
                    operation = asdict(meta)
                    if not meta.externalDocs:
                        del operation['externalDocs']
                    if not meta.reply:
                        del operation['reply']
                    del operation['message']

                    operations[operation_id] = {
                        'action': action,
                        'channel': {'$ref': f'#/channels/{channel_id}'},
                        'title': f'{action.capitalize()} {meta.message.title}',
                        'messages': [
                            {
                                '$ref': (
                                    f'#/channels/{channel_id}'
                                    f'/messages/{message_id}'
                                ),
                            },
                        ],
                        **operation,
                        'security': [
                            {'$ref': '#/components/securitySchemes/basicAuth'},
                            {
                                '$ref': (
                                    '#/components/securitySchemes/sessionAuth'
                                ),
                            },
                        ],
                    }
                if isinstance(meta, ws_info.Rejects):
                    message_id = f'{channel_id}_Error_{meta.status_code}'

                    message = {
                        'name': f'Error_{meta.status_code}',
                        'title': f'Websocket error {meta.status_code}',
                        'description': meta.details,
                        'contentType': 'application/json',
                        'payload': {
                            'type': 'object',
                            'required': ['code', 'reason'],
                            'properties': {
                                'code': {
                                    'type': 'integer',
                                    'description': 'Websocket error code',
                                },
                                'reason': {
                                    'type': 'string',
                                    'description': 'Reason of error',
                                },
                            },
                        },
                    }

                    components['messages'][message_id] = message
                    error_messages[message_id] = {
                        '$ref': f'#/components/messages/{message_id}',
                    }

        channels[channel_id] = {
            'address': route.path,
            'messages': messages | error_messages,
            'title': '',
            'summary': '',
            'description': '',
            'servers': [{'$ref': f'#/servers/{server_name}'}],
            'parameters': parameters,
            'bindings': {},
        }

    asyncapi['channels'] = channels

    return asyncapi


def dump_asyncapi_schema(schema: dict[str, Any]) -> str:
    """Serialize asyncapi schema to YAML.

    Parameters
    ----------
    schema : dict[str, Any]
        AsyncAPI schema dict.

    Returns
    -------
    str
        Schema serialized as YAML document.

    """
    return yaml.dump(schema, sort_keys=False, allow_unicode=True)
