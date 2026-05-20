// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from aqua_interfaces:msg/TankPhysicalVariables.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__STRUCT_HPP_
#define AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__aqua_interfaces__msg__TankPhysicalVariables __attribute__((deprecated))
#else
# define DEPRECATED__aqua_interfaces__msg__TankPhysicalVariables __declspec(deprecated)
#endif

namespace aqua_interfaces
{

namespace msg
{

// message struct
template<class ContainerAllocator>
struct TankPhysicalVariables_
{
  using Type = TankPhysicalVariables_<ContainerAllocator>;

  explicit TankPhysicalVariables_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->buoyancy = 0.0f;
      this->drag = 0.0f;
      this->lift = 0.0f;
      this->viscosity = 0.0f;
    }
  }

  explicit TankPhysicalVariables_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->buoyancy = 0.0f;
      this->drag = 0.0f;
      this->lift = 0.0f;
      this->viscosity = 0.0f;
    }
  }

  // field types and members
  using _buoyancy_type =
    float;
  _buoyancy_type buoyancy;
  using _drag_type =
    float;
  _drag_type drag;
  using _lift_type =
    float;
  _lift_type lift;
  using _viscosity_type =
    float;
  _viscosity_type viscosity;

  // setters for named parameter idiom
  Type & set__buoyancy(
    const float & _arg)
  {
    this->buoyancy = _arg;
    return *this;
  }
  Type & set__drag(
    const float & _arg)
  {
    this->drag = _arg;
    return *this;
  }
  Type & set__lift(
    const float & _arg)
  {
    this->lift = _arg;
    return *this;
  }
  Type & set__viscosity(
    const float & _arg)
  {
    this->viscosity = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    aqua_interfaces::msg::TankPhysicalVariables_<ContainerAllocator> *;
  using ConstRawPtr =
    const aqua_interfaces::msg::TankPhysicalVariables_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<aqua_interfaces::msg::TankPhysicalVariables_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<aqua_interfaces::msg::TankPhysicalVariables_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::msg::TankPhysicalVariables_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::msg::TankPhysicalVariables_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::msg::TankPhysicalVariables_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::msg::TankPhysicalVariables_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<aqua_interfaces::msg::TankPhysicalVariables_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<aqua_interfaces::msg::TankPhysicalVariables_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__aqua_interfaces__msg__TankPhysicalVariables
    std::shared_ptr<aqua_interfaces::msg::TankPhysicalVariables_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__aqua_interfaces__msg__TankPhysicalVariables
    std::shared_ptr<aqua_interfaces::msg::TankPhysicalVariables_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const TankPhysicalVariables_ & other) const
  {
    if (this->buoyancy != other.buoyancy) {
      return false;
    }
    if (this->drag != other.drag) {
      return false;
    }
    if (this->lift != other.lift) {
      return false;
    }
    if (this->viscosity != other.viscosity) {
      return false;
    }
    return true;
  }
  bool operator!=(const TankPhysicalVariables_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct TankPhysicalVariables_

// alias to use template instance with default allocator
using TankPhysicalVariables =
  aqua_interfaces::msg::TankPhysicalVariables_<std::allocator<void>>;

// constant definitions

}  // namespace msg

}  // namespace aqua_interfaces

#endif  // AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__STRUCT_HPP_
