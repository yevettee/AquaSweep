# generated from rosidl_generator_py/resource/_idl.py.em
# with input from aqua_interfaces:msg/TankStatus.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_TankStatus(type):
    """Metaclass of message 'TankStatus'."""

    _CREATE_ROS_MESSAGE = None
    _CONVERT_FROM_PY = None
    _CONVERT_TO_PY = None
    _DESTROY_ROS_MESSAGE = None
    _TYPE_SUPPORT = None

    __constants = {
    }

    @classmethod
    def __import_type_support__(cls):
        try:
            from rosidl_generator_py import import_type_support
            module = import_type_support('aqua_interfaces')
        except ImportError:
            import logging
            import traceback
            logger = logging.getLogger(
                'aqua_interfaces.msg.TankStatus')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__tank_status
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__tank_status
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__tank_status
            cls._TYPE_SUPPORT = module.type_support_msg__msg__tank_status
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__tank_status

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class TankStatus(metaclass=Metaclass_TankStatus):
    """Message class 'TankStatus'."""

    __slots__ = [
        '_pollution_level',
        '_fish_type',
        '_fish_count',
        '_fish_count_suspicious',
    ]

    _fields_and_field_types = {
        'pollution_level': 'float',
        'fish_type': 'string',
        'fish_count': 'int32',
        'fish_count_suspicious': 'int32',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.UnboundedString(),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
        rosidl_parser.definition.BasicType('int32'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.pollution_level = kwargs.get('pollution_level', float())
        self.fish_type = kwargs.get('fish_type', str())
        self.fish_count = kwargs.get('fish_count', int())
        self.fish_count_suspicious = kwargs.get('fish_count_suspicious', int())

    def __repr__(self):
        typename = self.__class__.__module__.split('.')
        typename.pop()
        typename.append(self.__class__.__name__)
        args = []
        for s, t in zip(self.__slots__, self.SLOT_TYPES):
            field = getattr(self, s)
            fieldstr = repr(field)
            # We use Python array type for fields that can be directly stored
            # in them, and "normal" sequences for everything else.  If it is
            # a type that we store in an array, strip off the 'array' portion.
            if (
                isinstance(t, rosidl_parser.definition.AbstractSequence) and
                isinstance(t.value_type, rosidl_parser.definition.BasicType) and
                t.value_type.typename in ['float', 'double', 'int8', 'uint8', 'int16', 'uint16', 'int32', 'uint32', 'int64', 'uint64']
            ):
                if len(field) == 0:
                    fieldstr = '[]'
                else:
                    assert fieldstr.startswith('array(')
                    prefix = "array('X', "
                    suffix = ')'
                    fieldstr = fieldstr[len(prefix):-len(suffix)]
            args.append(s[1:] + '=' + fieldstr)
        return '%s(%s)' % ('.'.join(typename), ', '.join(args))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        if self.pollution_level != other.pollution_level:
            return False
        if self.fish_type != other.fish_type:
            return False
        if self.fish_count != other.fish_count:
            return False
        if self.fish_count_suspicious != other.fish_count_suspicious:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def pollution_level(self):
        """Message field 'pollution_level'."""
        return self._pollution_level

    @pollution_level.setter
    def pollution_level(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'pollution_level' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'pollution_level' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._pollution_level = value

    @builtins.property
    def fish_type(self):
        """Message field 'fish_type'."""
        return self._fish_type

    @fish_type.setter
    def fish_type(self, value):
        if __debug__:
            assert \
                isinstance(value, str), \
                "The 'fish_type' field must be of type 'str'"
        self._fish_type = value

    @builtins.property
    def fish_count(self):
        """Message field 'fish_count'."""
        return self._fish_count

    @fish_count.setter
    def fish_count(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'fish_count' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'fish_count' field must be an integer in [-2147483648, 2147483647]"
        self._fish_count = value

    @builtins.property
    def fish_count_suspicious(self):
        """Message field 'fish_count_suspicious'."""
        return self._fish_count_suspicious

    @fish_count_suspicious.setter
    def fish_count_suspicious(self, value):
        if __debug__:
            assert \
                isinstance(value, int), \
                "The 'fish_count_suspicious' field must be of type 'int'"
            assert value >= -2147483648 and value < 2147483648, \
                "The 'fish_count_suspicious' field must be an integer in [-2147483648, 2147483647]"
        self._fish_count_suspicious = value
