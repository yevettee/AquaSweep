// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from aqua_interfaces:msg/RobotStatus.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__MSG__DETAIL__ROBOT_STATUS__TRAITS_HPP_
#define AQUA_INTERFACES__MSG__DETAIL__ROBOT_STATUS__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "aqua_interfaces/msg/detail/robot_status__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace aqua_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const RobotStatus & msg,
  std::ostream & out)
{
  out << "{";
  // member: state
  {
    out << "state: ";
    rosidl_generator_traits::value_to_yaml(msg.state, out);
    out << ", ";
  }

  // member: battery_level
  {
    out << "battery_level: ";
    rosidl_generator_traits::value_to_yaml(msg.battery_level, out);
    out << ", ";
  }

  // member: collision_force
  {
    out << "collision_force: ";
    rosidl_generator_traits::value_to_yaml(msg.collision_force, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const RobotStatus & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: state
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "state: ";
    rosidl_generator_traits::value_to_yaml(msg.state, out);
    out << "\n";
  }

  // member: battery_level
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "battery_level: ";
    rosidl_generator_traits::value_to_yaml(msg.battery_level, out);
    out << "\n";
  }

  // member: collision_force
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "collision_force: ";
    rosidl_generator_traits::value_to_yaml(msg.collision_force, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const RobotStatus & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace aqua_interfaces

namespace rosidl_generator_traits
{

[[deprecated("use aqua_interfaces::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const aqua_interfaces::msg::RobotStatus & msg,
  std::ostream & out, size_t indentation = 0)
{
  aqua_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use aqua_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const aqua_interfaces::msg::RobotStatus & msg)
{
  return aqua_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<aqua_interfaces::msg::RobotStatus>()
{
  return "aqua_interfaces::msg::RobotStatus";
}

template<>
inline const char * name<aqua_interfaces::msg::RobotStatus>()
{
  return "aqua_interfaces/msg/RobotStatus";
}

template<>
struct has_fixed_size<aqua_interfaces::msg::RobotStatus>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<aqua_interfaces::msg::RobotStatus>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<aqua_interfaces::msg::RobotStatus>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // AQUA_INTERFACES__MSG__DETAIL__ROBOT_STATUS__TRAITS_HPP_
