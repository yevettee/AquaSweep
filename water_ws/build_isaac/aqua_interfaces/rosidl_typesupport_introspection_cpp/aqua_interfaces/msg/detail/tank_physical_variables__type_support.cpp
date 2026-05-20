// generated from rosidl_typesupport_introspection_cpp/resource/idl__type_support.cpp.em
// with input from aqua_interfaces:msg/TankPhysicalVariables.idl
// generated code does not contain a copyright notice

#include "array"
#include "cstddef"
#include "string"
#include "vector"
#include "rosidl_runtime_c/message_type_support_struct.h"
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_interface/macros.h"
#include "aqua_interfaces/msg/detail/tank_physical_variables__struct.hpp"
#include "rosidl_typesupport_introspection_cpp/field_types.hpp"
#include "rosidl_typesupport_introspection_cpp/identifier.hpp"
#include "rosidl_typesupport_introspection_cpp/message_introspection.hpp"
#include "rosidl_typesupport_introspection_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_introspection_cpp/visibility_control.h"

namespace aqua_interfaces
{

namespace msg
{

namespace rosidl_typesupport_introspection_cpp
{

void TankPhysicalVariables_init_function(
  void * message_memory, rosidl_runtime_cpp::MessageInitialization _init)
{
  new (message_memory) aqua_interfaces::msg::TankPhysicalVariables(_init);
}

void TankPhysicalVariables_fini_function(void * message_memory)
{
  auto typed_message = static_cast<aqua_interfaces::msg::TankPhysicalVariables *>(message_memory);
  typed_message->~TankPhysicalVariables();
}

static const ::rosidl_typesupport_introspection_cpp::MessageMember TankPhysicalVariables_message_member_array[4] = {
  {
    "buoyancy",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_FLOAT,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(aqua_interfaces::msg::TankPhysicalVariables, buoyancy),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  },
  {
    "drag",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_FLOAT,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(aqua_interfaces::msg::TankPhysicalVariables, drag),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  },
  {
    "lift",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_FLOAT,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(aqua_interfaces::msg::TankPhysicalVariables, lift),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  },
  {
    "viscosity",  // name
    ::rosidl_typesupport_introspection_cpp::ROS_TYPE_FLOAT,  // type
    0,  // upper bound of string
    nullptr,  // members of sub message
    false,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(aqua_interfaces::msg::TankPhysicalVariables, viscosity),  // bytes offset in struct
    nullptr,  // default value
    nullptr,  // size() function pointer
    nullptr,  // get_const(index) function pointer
    nullptr,  // get(index) function pointer
    nullptr,  // fetch(index, &value) function pointer
    nullptr,  // assign(index, value) function pointer
    nullptr  // resize(index) function pointer
  }
};

static const ::rosidl_typesupport_introspection_cpp::MessageMembers TankPhysicalVariables_message_members = {
  "aqua_interfaces::msg",  // message namespace
  "TankPhysicalVariables",  // message name
  4,  // number of fields
  sizeof(aqua_interfaces::msg::TankPhysicalVariables),
  TankPhysicalVariables_message_member_array,  // message members
  TankPhysicalVariables_init_function,  // function to initialize message memory (memory has to be allocated)
  TankPhysicalVariables_fini_function  // function to terminate message instance (will not free memory)
};

static const rosidl_message_type_support_t TankPhysicalVariables_message_type_support_handle = {
  ::rosidl_typesupport_introspection_cpp::typesupport_identifier,
  &TankPhysicalVariables_message_members,
  get_message_typesupport_handle_function,
};

}  // namespace rosidl_typesupport_introspection_cpp

}  // namespace msg

}  // namespace aqua_interfaces


namespace rosidl_typesupport_introspection_cpp
{

template<>
ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
get_message_type_support_handle<aqua_interfaces::msg::TankPhysicalVariables>()
{
  return &::aqua_interfaces::msg::rosidl_typesupport_introspection_cpp::TankPhysicalVariables_message_type_support_handle;
}

}  // namespace rosidl_typesupport_introspection_cpp

#ifdef __cplusplus
extern "C"
{
#endif

ROSIDL_TYPESUPPORT_INTROSPECTION_CPP_PUBLIC
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_cpp, aqua_interfaces, msg, TankPhysicalVariables)() {
  return &::aqua_interfaces::msg::rosidl_typesupport_introspection_cpp::TankPhysicalVariables_message_type_support_handle;
}

#ifdef __cplusplus
}
#endif
