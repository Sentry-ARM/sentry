# Copyright © 2011-present, Encode OSS Ltd.
# Copyright © 2019-present, T. Franzel <tfranzel@gmail.com>, Cashlink Technologies GmbH.

# All rights reserved.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.

# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.

# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import collections
import inspect
import typing
from collections import defaultdict
from enum import Enum
from types import UnionType
from typing import Any, Literal, Union
from typing import get_type_hints as _get_type_hints
from typing import is_typeddict

import drf_spectacular
from drf_spectacular.drainage import get_override
from drf_spectacular.plumbing import UnableToProceedError
from drf_spectacular.plumbing import build_array_type as drf_build_array_type
from drf_spectacular.plumbing import build_basic_type, build_object_type, is_basic_type
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import _SchemaType

from sentry.apidocs.utils import reload_module_with_type_checking_enabled

# This function is ported from the drf-spectacular library method here:
# https://github.com/tfranzel/drf-spectacular/blob/03d315ced245db71cef1e45fd05a082b7dedc7aa/drf_spectacular/plumbing.py#L1100
# with modifications to support our use case:
#   grabbing description from a TypedDict __doc__
#   support for TypedDict required fields
#   support for excluded fields via @extend_schema_serializer

# TODO:
#   figure out solution for field descriptions
#   support deprecated fields via extension
#   map TypedDicts in schema registry


def get_type_hints(hint, **kwargs):
    try:
        return _get_type_hints(hint, **kwargs)
    except NameError:
        # try to resolve a circular import from TYPE_CHECKING imports
        reload_module_with_type_checking_enabled(hint.__module__)
        return _get_type_hints(hint, **kwargs)
    except TypeError:
        raise UnableToProceedError(
            f"""Unable to resolve type hints for {hint}.
            Please use types imported from `typing` instead of the types enabled
            by PEP585 (`from __future__ import annotations`).
            e.g. instead of list[str], please use List[str]."""
        )


def _get_type_hint_origin(hint):
    return typing.get_origin(hint), typing.get_args(hint)


def build_choice_description_list(choices) -> str:
    """
    Override the default generated description for choicefields if the value and
    label are identical to be (* `value`) instead of (* `value` - `label`).
    """
    return "\n".join(
        f"* `{value}` - {label}" if value != label else f"* `{value}`" for value, label in choices
    )


# Monkey patch build_choice_description_list
drf_spectacular.plumbing.build_choice_description_list = build_choice_description_list


def build_array_type(
    schema: _SchemaType | None, min_length: int | None = None, max_length: int | None = None
):
    """
    This function wraps the build_array_type from `drf-spectacular` because it is not type-safe.
    """
    if schema is None:
        raise ValueError("Schema cannot be None")
    return drf_build_array_type(schema=schema, min_length=min_length, max_length=max_length)


def resolve_type_hint(hint) -> Any:
    """drf-spectacular library method modified as described above"""
    origin, args = _get_type_hint_origin(hint)
    excluded_fields = get_override(hint, "exclude_fields", [])

    if origin is None and is_basic_type(hint, allow_none=False):
        return build_basic_type(hint)
    elif origin is None and inspect.isclass(hint) and issubclass(hint, tuple):
        # a convoluted way to catch NamedTuple. suggestions welcome.
        if get_type_hints(hint):
            properties = {k: resolve_type_hint(v) for k, v in get_type_hints(hint).items()}
        else:
            properties = {k: build_basic_type(OpenApiTypes.ANY) for k in hint._fields}  # type: ignore[attr-defined]
        return build_object_type(properties=properties, required=properties.keys())
    elif origin is list or hint is list:
        return build_array_type(
            resolve_type_hint(args[0]) if args else build_basic_type(OpenApiTypes.ANY)
        )
    elif origin is tuple:
        return build_array_type(
            schema=build_basic_type(args[0]),
            max_length=len(args),
            min_length=len(args),
        )
    elif origin is dict or origin is defaultdict:
        schema = build_basic_type(OpenApiTypes.OBJECT)
        if args and args[1] is not typing.Any and schema is not None:
            schema["additionalProperties"] = resolve_type_hint(args[1])
        return schema
    elif origin is set:
        return build_array_type(resolve_type_hint(args[0]))
    elif origin is frozenset:
        return build_array_type(resolve_type_hint(args[0]))
    elif origin is Literal:
        # Literal only works for python >= 3.8 despite typing_extensions, because it
        # behaves slightly different w.r.t. __origin__
        schema = {"enum": list(args)}
        if all(type(args[0]) is type(choice) for choice in args):
            basic_type = build_basic_type(type(args[0]))
            if basic_type is None:
                raise ValueError(f"Cannot update schema with None type: {type(args[0])}")
            schema.update(basic_type)
        return schema
    elif inspect.isclass(hint) and issubclass(hint, Enum):
        schema = {"enum": [item.value for item in hint]}
        mixin_base_types = [t for t in hint.__mro__ if is_basic_type(t)]
        if mixin_base_types:
            basic_type = build_basic_type(mixin_base_types[0])
            if basic_type is None:
                raise ValueError(f"Cannot update schema with None type: {mixin_base_types[0]}")
            schema.update(basic_type)
        return schema
    elif is_typeddict(hint):
        return build_object_type(
            properties={
                k: resolve_type_hint(v)
                for k, v in get_type_hints(hint).items()
                if k not in excluded_fields
            },
            description=inspect.cleandoc(hint.__doc__ or ""),
            required=[h for h in hint.__required_keys__ if h not in excluded_fields],
        )
    elif origin is Union or origin is UnionType:
        type_args = [arg for arg in args if arg is not type(None)]
        if len(type_args) > 1:
            # We use anyOf instead of oneOf (which DRF uses) b/c there's cases
            # where you can have int | float | long, where a valid value can be
            # multiple types but errors with oneOf.
            # TODO(schew2381): Create issue in drf-spectacular to see if this
            # fix makes sense
            schema = {"anyOf": [resolve_type_hint(arg) for arg in type_args]}
        else:
            schema = resolve_type_hint(type_args[0])
        if type(None) in args and schema is not None:
            # There's an issue where if 3 or more types are OR'd together and one of
            # them is None, validating the schema will fail because "nullable: true"
            # with "anyOf" raises an error because there is no "type" key on the
            # schema. This works around it by including a proxy null object in
            # the "anyOf".
            # See:
            #   - https://github.com/tfranzel/drf-spectacular/issues/925
            #   - https://github.com/OAI/OpenAPI-Specification/issues/1368.
            if len(args) > 2:
                schema["anyOf"].append({"type": "object", "nullable": True})
            else:
                schema["nullable"] = True
        return schema
    elif origin is collections.abc.Iterable:
        return build_array_type(resolve_type_hint(args[0]))
    else:
        raise UnableToProceedError(hint)
