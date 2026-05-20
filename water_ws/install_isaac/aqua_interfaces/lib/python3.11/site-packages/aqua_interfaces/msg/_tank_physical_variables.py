# generated from rosidl_generator_py/resource/_idl.py.em
# with input from aqua_interfaces:msg/TankPhysicalVariables.idl
# generated code does not contain a copyright notice


# Import statements for member types

import builtins  # noqa: E402, I100

import math  # noqa: E402, I100

import rosidl_parser.definition  # noqa: E402, I100


class Metaclass_TankPhysicalVariables(type):
    """Metaclass of message 'TankPhysicalVariables'."""

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
                'aqua_interfaces.msg.TankPhysicalVariables')
            logger.debug(
                'Failed to import needed modules for type support:\n' +
                traceback.format_exc())
        else:
            cls._CREATE_ROS_MESSAGE = module.create_ros_message_msg__msg__tank_physical_variables
            cls._CONVERT_FROM_PY = module.convert_from_py_msg__msg__tank_physical_variables
            cls._CONVERT_TO_PY = module.convert_to_py_msg__msg__tank_physical_variables
            cls._TYPE_SUPPORT = module.type_support_msg__msg__tank_physical_variables
            cls._DESTROY_ROS_MESSAGE = module.destroy_ros_message_msg__msg__tank_physical_variables

    @classmethod
    def __prepare__(cls, name, bases, **kwargs):
        # list constant names here so that they appear in the help text of
        # the message class under "Data and other attributes defined here:"
        # as well as populate each message instance
        return {
        }


class TankPhysicalVariables(metaclass=Metaclass_TankPhysicalVariables):
    """Message class 'TankPhysicalVariables'."""

    __slots__ = [
        '_buoyancy',
        '_drag',
        '_lift',
        '_viscosity',
    ]

    _fields_and_field_types = {
        'buoyancy': 'float',
        'drag': 'float',
        'lift': 'float',
        'viscosity': 'float',
    }

    SLOT_TYPES = (
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
        rosidl_parser.definition.BasicType('float'),  # noqa: E501
    )

    def __init__(self, **kwargs):
        assert all('_' + key in self.__slots__ for key in kwargs.keys()), \
            'Invalid arguments passed to constructor: %s' % \
            ', '.join(sorted(k for k in kwargs.keys() if '_' + k not in self.__slots__))
        self.buoyancy = kwargs.get('buoyancy', float())
        self.drag = kwargs.get('drag', float())
        self.lift = kwargs.get('lift', float())
        self.viscosity = kwargs.get('viscosity', float())

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
        if self.buoyancy != other.buoyancy:
            return False
        if self.drag != other.drag:
            return False
        if self.lift != other.lift:
            return False
        if self.viscosity != other.viscosity:
            return False
        return True

    @classmethod
    def get_fields_and_field_types(cls):
        from copy import copy
        return copy(cls._fields_and_field_types)

    @builtins.property
    def buoyancy(self):
        """Message field 'buoyancy'."""
        return self._buoyancy

    @buoyancy.setter
    def buoyancy(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'buoyancy' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'buoyancy' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._buoyancy = value

    @builtins.property
    def drag(self):
        """Message field 'drag'."""
        return self._drag

    @drag.setter
    def drag(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'drag' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'drag' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._drag = value

    @builtins.property
    def lift(self):
        """Message field 'lift'."""
        return self._lift

    @lift.setter
    def lift(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'lift' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'lift' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._lift = value

    @builtins.property
    def viscosity(self):
        """Message field 'viscosity'."""
        return self._viscosity

    @viscosity.setter
    def viscosity(self, value):
        if __debug__:
            assert \
                isinstance(value, float), \
                "The 'viscosity' field must be of type 'float'"
            assert not (value < -3.402823466e+38 or value > 3.402823466e+38) or math.isinf(value), \
                "The 'viscosity' field must be a float in [-3.402823466e+38, 3.402823466e+38]"
        self._viscosity = value
