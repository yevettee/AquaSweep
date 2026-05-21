// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from aqua_interfaces:msg/TankStatus.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "aqua_interfaces/msg/detail/tank_status__rosidl_typesupport_introspection_c.h"
#include "aqua_interfaces/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "aqua_interfaces/msg/detail/tank_status__functions.h"
#include "aqua_interfaces/msg/detail/tank_status__struct.h"


// Include directives for member types
// Member `fish_type`
#include "rosidl_runtime_c/string_functions.h"

#ifdef __cplusplus
extern "C"
{
#endif

void aqua_interfaces__msg__TankStatus__rosidl_typesupport_introspection_c__TankStatus_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  aqua_interfaces__msg__TankStatus__init(message_memory);
}

void aqua_interfaces__msg__TankStatus__rosidl_typesupport_introspection_c__TankStatus_fini_function(void * message_memory)
{
  aqua_interfaces__msg__TankStatus__fini(message_memory);
}

static rosidl_typesupport_introspection_c__MessageMember aqua_interfaces__msg__TankStatus__rosidl_typesupport_introspection_c__TankStatus_message_member_array[4] = {
  {
    "pollution_level",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_FLOAT,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(aqua_interfaces__msg__TankStatus, pollution_level),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "fish_type",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_STRING,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(aqua_interfaces__msg__TankStatus, fish_type),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "fish_count",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT32,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(aqua_interfaces__msg__TankStatus, fish_count),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  },
  {
    "fish_count_suspicious",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_INT32,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(aqua_interfaces__msg__TankStatus, fish_count_suspicious),  // bytes offset in struct
    NULL,  // default value
    NULL,  // size() function pointer
    NULL,  // get_const(index) function pointer
    NULL,  // get(index) function pointer
    NULL,  // fetch(index, &value) function pointer
    NULL,  // assign(index, value) function pointer
    NULL  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers aqua_interfaces__msg__TankStatus__rosidl_typesupport_introspection_c__TankStatus_message_members = {
  "aqua_interfaces__msg",  // message namespace
  "TankStatus",  // message name
  4,  // number of fields
  sizeof(aqua_interfaces__msg__TankStatus),
  aqua_interfaces__msg__TankStatus__rosidl_typesupport_introspection_c__TankStatus_message_member_array,  // message members
  aqua_interfaces__msg__TankStatus__rosidl_typesupport_introspection_c__TankStatus_init_function,  // function to initialize message memory (memory has to be allocated)
  aqua_interfaces__msg__TankStatus__rosidl_typesupport_introspection_c__TankStatus_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t aqua_interfaces__msg__TankStatus__rosidl_typesupport_introspection_c__TankStatus_message_type_support_handle = {
  0,
  &aqua_interfaces__msg__TankStatus__rosidl_typesupport_introspection_c__TankStatus_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_aqua_interfaces
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, aqua_interfaces, msg, TankStatus)() {
  if (!aqua_interfaces__msg__TankStatus__rosidl_typesupport_introspection_c__TankStatus_message_type_support_handle.typesupport_identifier) {
    aqua_interfaces__msg__TankStatus__rosidl_typesupport_introspection_c__TankStatus_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &aqua_interfaces__msg__TankStatus__rosidl_typesupport_introspection_c__TankStatus_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
