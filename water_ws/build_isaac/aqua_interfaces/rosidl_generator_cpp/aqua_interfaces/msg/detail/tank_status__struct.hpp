// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from aqua_interfaces:msg/TankStatus.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__MSG__DETAIL__TANK_STATUS__STRUCT_HPP_
#define AQUA_INTERFACES__MSG__DETAIL__TANK_STATUS__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__aqua_interfaces__msg__TankStatus __attribute__((deprecated))
#else
# define DEPRECATED__aqua_interfaces__msg__TankStatus __declspec(deprecated)
#endif

namespace aqua_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct TankStatus_
{
  using Type = TankStatus_<ContainerAllocator>;

  explicit TankStatus_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->pollution_level = 0.0f;
      this->fish_type = "";
      this->fish_count = 0l;
      this->fish_count_suspicious = 0l;
    }
  }

  explicit TankStatus_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : fish_type(_alloc)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->pollution_level = 0.0f;
      this->fish_type = "";
      this->fish_count = 0l;
      this->fish_count_suspicious = 0l;
    }
  }

  // field types and members
  using _pollution_level_type =
    float;
  _pollution_level_type pollution_level;
  using _fish_type_type =
    std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>>;
  _fish_type_type fish_type;
  using _fish_count_type =
    int32_t;
  _fish_count_type fish_count;
  using _fish_count_suspicious_type =
    int32_t;
  _fish_count_suspicious_type fish_count_suspicious;

  // setters for named parameter idiom
  Type & set__pollution_level(
    const float & _arg)
  {
    this->pollution_level = _arg;
    return *this;
  }
  Type & set__fish_type(
    const std::basic_string<char, std::char_traits<char>, typename std::allocator_traits<ContainerAllocator>::template rebind_alloc<char>> & _arg)
  {
    this->fish_type = _arg;
    return *this;
  }
  Type & set__fish_count(
    const int32_t & _arg)
  {
    this->fish_count = _arg;
    return *this;
  }
  Type & set__fish_count_suspicious(
    const int32_t & _arg)
  {
    this->fish_count_suspicious = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    aqua_interfaces::msg::TankStatus_<ContainerAllocator> *;
  using ConstRawPtr =
    const aqua_interfaces::msg::TankStatus_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<aqua_interfaces::msg::TankStatus_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<aqua_interfaces::msg::TankStatus_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::msg::TankStatus_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::msg::TankStatus_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::msg::TankStatus_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::msg::TankStatus_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<aqua_interfaces::msg::TankStatus_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<aqua_interfaces::msg::TankStatus_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__aqua_interfaces__msg__TankStatus
    std::shared_ptr<aqua_interfaces::msg::TankStatus_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__aqua_interfaces__msg__TankStatus
    std::shared_ptr<aqua_interfaces::msg::TankStatus_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const TankStatus_ & other) const
  {
    if (this->pollution_level != other.pollution_level) {
      return false;
    }
    if (this->fish_type != other.fish_type) {
      return false;
    }
    if (this->fish_count != other.fish_count) {
      return false;
    }
    if (this->fish_count_suspicious != other.fish_count_suspicious) {
      return false;
    }
    return true;
  }
  bool operator!=(const TankStatus_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct TankStatus_

// alias to use template instance with default allocator
using TankStatus =
  aqua_interfaces::msg::TankStatus_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace aqua_interfaces

#endif  // AQUA_INTERFACES__MSG__DETAIL__TANK_STATUS__STRUCT_HPP_
