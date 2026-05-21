// generated from rosidl_typesupport_fastrtps_cpp/resource/idl__type_support.cpp.em
// with input from aqua_interfaces:msg/TankStatus.idl
// generated code does not contain a copyright notice
#include "aqua_interfaces/msg/detail/tank_status__rosidl_typesupport_fastrtps_cpp.hpp"
#include "aqua_interfaces/msg/detail/tank_status__struct.hpp"

#include <limits>
#include <stdexcept>
#include <string>
#include "rosidl_typesupport_cpp/message_type_support.hpp"
#include "rosidl_typesupport_fastrtps_cpp/identifier.hpp"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support.h"
#include "rosidl_typesupport_fastrtps_cpp/message_type_support_decl.hpp"
#include "rosidl_typesupport_fastrtps_cpp/wstring_conversion.hpp"
#include "fastcdr/Cdr.h"


// forward declaration of message dependencies and their conversion functions

namespace aqua_interfaces
{

namespace msg
{

namespace typesupport_fastrtps_cpp
{

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_aqua_interfaces
cdr_serialize(
  const aqua_interfaces::msg::TankStatus & ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  // Member: pollution_level
  cdr << ros_message.pollution_level;
  // Member: fish_type
  cdr << ros_message.fish_type;
  // Member: fish_count
  cdr << ros_message.fish_count;
  // Member: fish_count_suspicious
  cdr << ros_message.fish_count_suspicious;
  return true;
}

bool
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_aqua_interfaces
cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  aqua_interfaces::msg::TankStatus & ros_message)
{
  // Member: pollution_level
  cdr >> ros_message.pollution_level;

  // Member: fish_type
  cdr >> ros_message.fish_type;

  // Member: fish_count
  cdr >> ros_message.fish_count;

  // Member: fish_count_suspicious
  cdr >> ros_message.fish_count_suspicious;

  return true;
}  // NOLINT(readability/fn_size)

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_aqua_interfaces
get_serialized_size(
  const aqua_interfaces::msg::TankStatus & ros_message,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  (void)padding;
  (void)wchar_size;

  // Member: pollution_level
  {
    size_t item_size = sizeof(ros_message.pollution_level);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: fish_type
  current_alignment += padding +
    eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
    (ros_message.fish_type.size() + 1);
  // Member: fish_count
  {
    size_t item_size = sizeof(ros_message.fish_count);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }
  // Member: fish_count_suspicious
  {
    size_t item_size = sizeof(ros_message.fish_count_suspicious);
    current_alignment += item_size +
      eprosima::fastcdr::Cdr::alignment(current_alignment, item_size);
  }

  return current_alignment - initial_alignment;
}

size_t
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_PUBLIC_aqua_interfaces
max_serialized_size_TankStatus(
  bool & full_bounded,
  bool & is_plain,
  size_t current_alignment)
{
  size_t initial_alignment = current_alignment;

  const size_t padding = 4;
  const size_t wchar_size = 4;
  size_t last_member_size = 0;
  (void)last_member_size;
  (void)padding;
  (void)wchar_size;

  full_bounded = true;
  is_plain = true;


  // Member: pollution_level
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }

  // Member: fish_type
  {
    size_t array_size = 1;

    full_bounded = false;
    is_plain = false;
    for (size_t index = 0; index < array_size; ++index) {
      current_alignment += padding +
        eprosima::fastcdr::Cdr::alignment(current_alignment, padding) +
        1;
    }
  }

  // Member: fish_count
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }

  // Member: fish_count_suspicious
  {
    size_t array_size = 1;

    last_member_size = array_size * sizeof(uint32_t);
    current_alignment += array_size * sizeof(uint32_t) +
      eprosima::fastcdr::Cdr::alignment(current_alignment, sizeof(uint32_t));
  }

  size_t ret_val = current_alignment - initial_alignment;
  if (is_plain) {
    // All members are plain, and type is not empty.
    // We still need to check that the in-memory alignment
    // is the same as the CDR mandated alignment.
    using DataType = aqua_interfaces::msg::TankStatus;
    is_plain =
      (
      offsetof(DataType, fish_count_suspicious) +
      last_member_size
      ) == ret_val;
  }

  return ret_val;
}

static bool _TankStatus__cdr_serialize(
  const void * untyped_ros_message,
  eprosima::fastcdr::Cdr & cdr)
{
  auto typed_message =
    static_cast<const aqua_interfaces::msg::TankStatus *>(
    untyped_ros_message);
  return cdr_serialize(*typed_message, cdr);
}

static bool _TankStatus__cdr_deserialize(
  eprosima::fastcdr::Cdr & cdr,
  void * untyped_ros_message)
{
  auto typed_message =
    static_cast<aqua_interfaces::msg::TankStatus *>(
    untyped_ros_message);
  return cdr_deserialize(cdr, *typed_message);
}

static uint32_t _TankStatus__get_serialized_size(
  const void * untyped_ros_message)
{
  auto typed_message =
    static_cast<const aqua_interfaces::msg::TankStatus *>(
    untyped_ros_message);
  return static_cast<uint32_t>(get_serialized_size(*typed_message, 0));
}

static size_t _TankStatus__max_serialized_size(char & bounds_info)
{
  bool full_bounded;
  bool is_plain;
  size_t ret_val;

  ret_val = max_serialized_size_TankStatus(full_bounded, is_plain, 0);

  bounds_info =
    is_plain ? ROSIDL_TYPESUPPORT_FASTRTPS_PLAIN_TYPE :
    full_bounded ? ROSIDL_TYPESUPPORT_FASTRTPS_BOUNDED_TYPE : ROSIDL_TYPESUPPORT_FASTRTPS_UNBOUNDED_TYPE;
  return ret_val;
}

static message_type_support_callbacks_t _TankStatus__callbacks = {
  "aqua_interfaces::msg",
  "TankStatus",
  _TankStatus__cdr_serialize,
  _TankStatus__cdr_deserialize,
  _TankStatus__get_serialized_size,
  _TankStatus__max_serialized_size
};

static rosidl_message_type_support_t _TankStatus__handle = {
  rosidl_typesupport_fastrtps_cpp::typesupport_identifier,
  &_TankStatus__callbacks,
  get_message_typesupport_handle_function,
};

}  // namespace typesupport_fastrtps_cpp

}  // namespace msg

}  // namespace aqua_interfaces

namespace rosidl_typesupport_fastrtps_cpp
{

template<>
ROSIDL_TYPESUPPORT_FASTRTPS_CPP_EXPORT_aqua_interfaces
const rosidl_message_type_support_t *
get_message_type_support_handle<aqua_interfaces::msg::TankStatus>()
{
  return &aqua_interfaces::msg::typesupport_fastrtps_cpp::_TankStatus__handle;
}

}  // namespace rosidl_typesupport_fastrtps_cpp

#ifdef __cplusplus
extern "C"
{
#endif

const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_fastrtps_cpp, aqua_interfaces, msg, TankStatus)() {
  return &aqua_interfaces::msg::typesupport_fastrtps_cpp::_TankStatus__handle;
}

#ifdef __cplusplus
}
#endif
