// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from aqua_interfaces:msg/TankStatus.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__MSG__DETAIL__TANK_STATUS__BUILDER_HPP_
#define AQUA_INTERFACES__MSG__DETAIL__TANK_STATUS__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "aqua_interfaces/msg/detail/tank_status__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace aqua_interfaces
{

namespace msg
{

namespace builder
{

class Init_TankStatus_fish_count_suspicious
{
public:
  explicit Init_TankStatus_fish_count_suspicious(::aqua_interfaces::msg::TankStatus & msg)
  : msg_(msg)
  {}
  ::aqua_interfaces::msg::TankStatus fish_count_suspicious(::aqua_interfaces::msg::TankStatus::_fish_count_suspicious_type arg)
  {
    msg_.fish_count_suspicious = std::move(arg);
    return std::move(msg_);
  }

private:
  ::aqua_interfaces::msg::TankStatus msg_;
};

class Init_TankStatus_fish_count
{
public:
  explicit Init_TankStatus_fish_count(::aqua_interfaces::msg::TankStatus & msg)
  : msg_(msg)
  {}
  Init_TankStatus_fish_count_suspicious fish_count(::aqua_interfaces::msg::TankStatus::_fish_count_type arg)
  {
    msg_.fish_count = std::move(arg);
    return Init_TankStatus_fish_count_suspicious(msg_);
  }

private:
  ::aqua_interfaces::msg::TankStatus msg_;
};

class Init_TankStatus_fish_type
{
public:
  explicit Init_TankStatus_fish_type(::aqua_interfaces::msg::TankStatus & msg)
  : msg_(msg)
  {}
  Init_TankStatus_fish_count fish_type(::aqua_interfaces::msg::TankStatus::_fish_type_type arg)
  {
    msg_.fish_type = std::move(arg);
    return Init_TankStatus_fish_count(msg_);
  }

private:
  ::aqua_interfaces::msg::TankStatus msg_;
};

class Init_TankStatus_pollution_level
{
public:
  Init_TankStatus_pollution_level()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_TankStatus_fish_type pollution_level(::aqua_interfaces::msg::TankStatus::_pollution_level_type arg)
  {
    msg_.pollution_level = std::move(arg);
    return Init_TankStatus_fish_type(msg_);
  }

private:
  ::aqua_interfaces::msg::TankStatus msg_;
};

}  // namespace builder

}  // namespace msg

template<typename MessageType>
auto build();

template<>
inline
auto build<::aqua_interfaces::msg::TankStatus>()
{
  return aqua_interfaces::msg::builder::Init_TankStatus_pollution_level();
}

}  // namespace aqua_interfaces

#endif  // AQUA_INTERFACES__MSG__DETAIL__TANK_STATUS__BUILDER_HPP_
