// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from aqua_interfaces:msg/TankPhysicalVariables.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__TRAITS_HPP_
#define AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "aqua_interfaces/msg/detail/tank_physical_variables__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace aqua_interfaces
{

namespace msg
{

inline void to_flow_style_yaml(
  const TankPhysicalVariables & msg,
  std::ostream & out)
{
  out << "{";
  // member: buoyancy
  {
    out << "buoyancy: ";
    rosidl_generator_traits::value_to_yaml(msg.buoyancy, out);
    out << ", ";
  }

  // member: drag
  {
    out << "drag: ";
    rosidl_generator_traits::value_to_yaml(msg.drag, out);
    out << ", ";
  }

  // member: lift
  {
    out << "lift: ";
    rosidl_generator_traits::value_to_yaml(msg.lift, out);
    out << ", ";
  }

  // member: viscosity
  {
    out << "viscosity: ";
    rosidl_generator_traits::value_to_yaml(msg.viscosity, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const TankPhysicalVariables & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: buoyancy
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "buoyancy: ";
    rosidl_generator_traits::value_to_yaml(msg.buoyancy, out);
    out << "\n";
  }

  // member: drag
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "drag: ";
    rosidl_generator_traits::value_to_yaml(msg.drag, out);
    out << "\n";
  }

  // member: lift
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "lift: ";
    rosidl_generator_traits::value_to_yaml(msg.lift, out);
    out << "\n";
  }

  // member: viscosity
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "viscosity: ";
    rosidl_generator_traits::value_to_yaml(msg.viscosity, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const TankPhysicalVariables & msg, bool use_flow_style = false)
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
  const aqua_interfaces::msg::TankPhysicalVariables & msg,
  std::ostream & out, size_t indentation = 0)
{
  aqua_interfaces::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use aqua_interfaces::msg::to_yaml() instead")]]
inline std::string to_yaml(const aqua_interfaces::msg::TankPhysicalVariables & msg)
{
  return aqua_interfaces::msg::to_yaml(msg);
}

template<>
inline const char * data_type<aqua_interfaces::msg::TankPhysicalVariables>()
{
  return "aqua_interfaces::msg::TankPhysicalVariables";
}

template<>
inline const char * name<aqua_interfaces::msg::TankPhysicalVariables>()
{
  return "aqua_interfaces/msg/TankPhysicalVariables";
}

template<>
struct has_fixed_size<aqua_interfaces::msg::TankPhysicalVariables>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<aqua_interfaces::msg::TankPhysicalVariables>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<aqua_interfaces::msg::TankPhysicalVariables>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__TRAITS_HPP_
