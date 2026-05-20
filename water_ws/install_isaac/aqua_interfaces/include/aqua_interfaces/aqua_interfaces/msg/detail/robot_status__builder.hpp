// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from aqua_interfaces:msg/RobotStatus.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__MSG__DETAIL__ROBOT_STATUS__BUILDER_HPP_
#define AQUA_INTERFACES__MSG__DETAIL__ROBOT_STATUS__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "aqua_interfaces/msg/detail/robot_status__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace aqua_interfaces
{

namespace msg
{

namespace builder
{

class Init_RobotStatus_collision_force
{
public:
  explicit Init_RobotStatus_collision_force(::aqua_interfaces::msg::RobotStatus & msg)
  : msg_(msg)
  {}
  ::aqua_interfaces::msg::RobotStatus collision_force(::aqua_interfaces::msg::RobotStatus::_collision_force_type arg)
  {
    msg_.collision_force = std::move(arg);
    return std::move(msg_);
  }

private:
  ::aqua_interfaces::msg::RobotStatus msg_;
};

class Init_RobotStatus_battery_level
{
public:
  explicit Init_RobotStatus_battery_level(::aqua_interfaces::msg::RobotStatus & msg)
  : msg_(msg)
  {}
  Init_RobotStatus_collision_force battery_level(::aqua_interfaces::msg::RobotStatus::_battery_level_type arg)
  {
    msg_.battery_level = std::move(arg);
    return Init_RobotStatus_collision_force(msg_);
  }

private:
  ::aqua_interfaces::msg::RobotStatus msg_;
};

class Init_RobotStatus_state
{
public:
  Init_RobotStatus_state()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_RobotStatus_battery_level state(::aqua_interfaces::msg::RobotStatus::_state_type arg)
  {
    msg_.state = std::move(arg);
    return Init_RobotStatus_battery_level(msg_);
  }

private:
  ::aqua_interfaces::msg::RobotStatus msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::aqua_interfaces::msg::RobotStatus>()
{
  return aqua_interfaces::msg::builder::Init_RobotStatus_state();
}

}  // namespace aqua_interfaces

#endif  // AQUA_INTERFACES__MSG__DETAIL__ROBOT_STATUS__BUILDER_HPP_
