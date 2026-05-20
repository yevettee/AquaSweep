// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from aqua_interfaces:msg/TankStatus.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__MSG__DETAIL__TANK_STATUS__TRAITS_HPP_
#define AQUA_INTERFACES__MSG__DETAIL__TANK_STATUS__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "aqua_interfaces/msg/detail/tank_status__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace aqua_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const TankStatus & msg,
  std::ostream & out)
{
  out << "{";
  // member: pollution_level
  {
    out << "pollution_level: ";
    rosidl_generator_traits::value_to_yaml(msg.pollution_level, out);
    out << ", ";
  }

  // member: fish_type
  {
    out << "fish_type: ";
    rosidl_generator_traits::value_to_yaml(msg.fish_type, out);
    out << ", ";
  }

  // member: fish_count
  {
    out << "fish_count: ";
    rosidl_generator_traits::value_to_yaml(msg.fish_count, out);
    out << ", ";
  }

  // member: fish_count_suspicious
  {
    out << "fish_count_suspicious: ";
    rosidl_generator_traits::value_to_yaml(msg.fish_count_suspicious, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const TankStatus & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: pollution_level
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "pollution_level: ";
    rosidl_generator_traits::value_to_yaml(msg.pollution_level, out);
    out << "\n";
  }

  // member: fish_type
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "fish_type: ";
    rosidl_generator_traits::value_to_yaml(msg.fish_type, out);
    out << "\n";
  }

  // member: fish_count
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "fish_count: ";
    rosidl_generator_traits::value_to_yaml(msg.fish_count, out);
    out << "\n";
  }

  // member: fish_count_suspicious
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "fish_count_suspicious: ";
    rosidl_generator_traits::value_to_yaml(msg.fish_count_suspicious, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const TankStatus & msg, bool use_flow_style = false)
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
  const aqua_interfaces::msg::TankStatus & msg,
  std::ostream & out, size_t indentation = 0)
{
  aqua_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use aqua_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const aqua_interfaces::msg::TankStatus & msg)
{
  return aqua_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<aqua_interfaces::msg::TankStatus>()
{
  return "aqua_interfaces::msg::TankStatus";
}

template<>
inline const char * name<aqua_interfaces::msg::TankStatus>()
{
  return "aqua_interfaces/msg/TankStatus";
}

template<>
struct has_fixed_size<aqua_interfaces::msg::TankStatus>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<aqua_interfaces::msg::TankStatus>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<aqua_interfaces::msg::TankStatus>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // AQUA_INTERFACES__MSG__DETAIL__TANK_STATUS__TRAITS_HPP_
