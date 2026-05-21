// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from aqua_interfaces:msg/TankPhysicalVariables.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__BUILDER_HPP_
#define AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "aqua_interfaces/msg/detail/tank_physical_variables__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace aqua_interfaces
{

namespace msg
{

namespace builder
{

class Init_TankPhysicalVariables_viscosity
{
public:
  explicit Init_TankPhysicalVariables_viscosity(::aqua_interfaces::msg::TankPhysicalVariables & msg)
  : msg_(msg)
  {}
  ::aqua_interfaces::msg::TankPhysicalVariables viscosity(::aqua_interfaces::msg::TankPhysicalVariables::_viscosity_type arg)
  {
    msg_.viscosity = std::move(arg);
    return std::move(msg_);
  }

private:
  ::aqua_interfaces::msg::TankPhysicalVariables msg_;
};

class Init_TankPhysicalVariables_lift
{
public:
  explicit Init_TankPhysicalVariables_lift(::aqua_interfaces::msg::TankPhysicalVariables & msg)
  : msg_(msg)
  {}
  Init_TankPhysicalVariables_viscosity lift(::aqua_interfaces::msg::TankPhysicalVariables::_lift_type arg)
  {
    msg_.lift = std::move(arg);
    return Init_TankPhysicalVariables_viscosity(msg_);
  }

private:
  ::aqua_interfaces::msg::TankPhysicalVariables msg_;
};

class Init_TankPhysicalVariables_drag
{
public:
  explicit Init_TankPhysicalVariables_drag(::aqua_interfaces::msg::TankPhysicalVariables & msg)
  : msg_(msg)
  {}
  Init_TankPhysicalVariables_lift drag(::aqua_interfaces::msg::TankPhysicalVariables::_drag_type arg)
  {
    msg_.drag = std::move(arg);
    return Init_TankPhysicalVariables_lift(msg_);
  }

private:
  ::aqua_interfaces::msg::TankPhysicalVariables msg_;
};

class Init_TankPhysicalVariables_buoyancy
{
public:
  Init_TankPhysicalVariables_buoyancy()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_TankPhysicalVariables_drag buoyancy(::aqua_interfaces::msg::TankPhysicalVariables::_buoyancy_type arg)
  {
    msg_.buoyancy = std::move(arg);
    return Init_TankPhysicalVariables_drag(msg_);
  }

private:
  ::aqua_interfaces::msg::TankPhysicalVariables msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::aqua_interfaces::msg::TankPhysicalVariables>()
{
  return aqua_interfaces::msg::builder::Init_TankPhysicalVariables_buoyancy();
}

}  // namespace aqua_interfaces

#endif  // AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__BUILDER_HPP_
