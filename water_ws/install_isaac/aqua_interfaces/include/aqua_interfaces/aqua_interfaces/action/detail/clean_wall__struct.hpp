// generated from rosidl_generator_cpp/resource/idl__struct.hpp.em
// with input from aqua_interfaces:action/CleanWall.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__ACTION__DETAIL__CLEAN_WALL__STRUCT_HPP_
#define AQUA_INTERFACES__ACTION__DETAIL__CLEAN_WALL__STRUCT_HPP_

#include <algorithm>
#include <array>
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

#include "rosidl_runtime_cpp/bounded_vector.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


#ifndef _WIN32
# define DEPRECATED__aqua_interfaces__action__CleanWall_Goal __attribute__((deprecated))
#else
# define DEPRECATED__aqua_interfaces__action__CleanWall_Goal __declspec(deprecated)
#endif

namespace aqua_interfaces
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct CleanWall_Goal_
{
  using Type = CleanWall_Goal_<ContainerAllocator>;

  explicit CleanWall_Goal_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->structure_needs_at_least_one_member = 0;
    }
  }

  explicit CleanWall_Goal_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->structure_needs_at_least_one_member = 0;
    }
  }

  // field types and members
  using _structure_needs_at_least_one_member_type =
    uint8_t;
  _structure_needs_at_least_one_member_type structure_needs_at_least_one_member;


  // constant declarations

  // pointer types
  using RawPtr =
    aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator> *;
  using ConstRawPtr =
    const aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_Goal
    std::shared_ptr<aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_Goal
    std::shared_ptr<aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const CleanWall_Goal_ & other) const
  {
    if (this->structure_needs_at_least_one_member != other.structure_needs_at_least_one_member) {
      return false;
    }
    return true;
  }
  bool operator!=(const CleanWall_Goal_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct CleanWall_Goal_

// alias to use template instance with default allocator
using CleanWall_Goal =
  aqua_interfaces::action::CleanWall_Goal_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace aqua_interfaces


#ifndef _WIN32
# define DEPRECATED__aqua_interfaces__action__CleanWall_Result __attribute__((deprecated))
#else
# define DEPRECATED__aqua_interfaces__action__CleanWall_Result __declspec(deprecated)
#endif

namespace aqua_interfaces
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct CleanWall_Result_
{
  using Type = CleanWall_Result_<ContainerAllocator>;

  explicit CleanWall_Result_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->success = false;
    }
  }

  explicit CleanWall_Result_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->success = false;
    }
  }

  // field types and members
  using _success_type =
    bool;
  _success_type success;

  // setters for named parameter idiom
  Type & set__success(
    const bool & _arg)
  {
    this->success = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    aqua_interfaces::action::CleanWall_Result_<ContainerAllocator> *;
  using ConstRawPtr =
    const aqua_interfaces::action::CleanWall_Result_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_Result_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_Result_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_Result_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_Result_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_Result_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_Result_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_Result_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_Result_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_Result
    std::shared_ptr<aqua_interfaces::action::CleanWall_Result_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_Result
    std::shared_ptr<aqua_interfaces::action::CleanWall_Result_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const CleanWall_Result_ & other) const
  {
    if (this->success != other.success) {
      return false;
    }
    return true;
  }
  bool operator!=(const CleanWall_Result_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct CleanWall_Result_

// alias to use template instance with default allocator
using CleanWall_Result =
  aqua_interfaces::action::CleanWall_Result_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace aqua_interfaces


#ifndef _WIN32
# define DEPRECATED__aqua_interfaces__action__CleanWall_Feedback __attribute__((deprecated))
#else
# define DEPRECATED__aqua_interfaces__action__CleanWall_Feedback __declspec(deprecated)
#endif

namespace aqua_interfaces
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct CleanWall_Feedback_
{
  using Type = CleanWall_Feedback_<ContainerAllocator>;

  explicit CleanWall_Feedback_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->progress = 0.0f;
    }
  }

  explicit CleanWall_Feedback_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  {
    (void)_alloc;
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->progress = 0.0f;
    }
  }

  // field types and members
  using _progress_type =
    float;
  _progress_type progress;

  // setters for named parameter idiom
  Type & set__progress(
    const float & _arg)
  {
    this->progress = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator> *;
  using ConstRawPtr =
    const aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_Feedback
    std::shared_ptr<aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_Feedback
    std::shared_ptr<aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const CleanWall_Feedback_ & other) const
  {
    if (this->progress != other.progress) {
      return false;
    }
    return true;
  }
  bool operator!=(const CleanWall_Feedback_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct CleanWall_Feedback_

// alias to use template instance with default allocator
using CleanWall_Feedback =
  aqua_interfaces::action::CleanWall_Feedback_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace aqua_interfaces


// Include directives for member types
// Member 'goal_id'
#include "unique_identifier_msgs/msg/detail/uuid__struct.hpp"
// Member 'goal'
#include "aqua_interfaces/action/detail/clean_wall__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__aqua_interfaces__action__CleanWall_SendGoal_Request __attribute__((deprecated))
#else
# define DEPRECATED__aqua_interfaces__action__CleanWall_SendGoal_Request __declspec(deprecated)
#endif

namespace aqua_interfaces
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct CleanWall_SendGoal_Request_
{
  using Type = CleanWall_SendGoal_Request_<ContainerAllocator>;

  explicit CleanWall_SendGoal_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_init),
    goal(_init)
  {
    (void)_init;
  }

  explicit CleanWall_SendGoal_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_alloc, _init),
    goal(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _goal_id_type =
    unique_identifier_msgs::msg::UUID_<ContainerAllocator>;
  _goal_id_type goal_id;
  using _goal_type =
    aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator>;
  _goal_type goal;

  // setters for named parameter idiom
  Type & set__goal_id(
    const unique_identifier_msgs::msg::UUID_<ContainerAllocator> & _arg)
  {
    this->goal_id = _arg;
    return *this;
  }
  Type & set__goal(
    const aqua_interfaces::action::CleanWall_Goal_<ContainerAllocator> & _arg)
  {
    this->goal = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    aqua_interfaces::action::CleanWall_SendGoal_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const aqua_interfaces::action::CleanWall_SendGoal_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_SendGoal_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_SendGoal_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_SendGoal_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_SendGoal_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_SendGoal_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_SendGoal_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_SendGoal_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_SendGoal_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_SendGoal_Request
    std::shared_ptr<aqua_interfaces::action::CleanWall_SendGoal_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_SendGoal_Request
    std::shared_ptr<aqua_interfaces::action::CleanWall_SendGoal_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const CleanWall_SendGoal_Request_ & other) const
  {
    if (this->goal_id != other.goal_id) {
      return false;
    }
    if (this->goal != other.goal) {
      return false;
    }
    return true;
  }
  bool operator!=(const CleanWall_SendGoal_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct CleanWall_SendGoal_Request_

// alias to use template instance with default allocator
using CleanWall_SendGoal_Request =
  aqua_interfaces::action::CleanWall_SendGoal_Request_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace aqua_interfaces


// Include directives for member types
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__aqua_interfaces__action__CleanWall_SendGoal_Response __attribute__((deprecated))
#else
# define DEPRECATED__aqua_interfaces__action__CleanWall_SendGoal_Response __declspec(deprecated)
#endif

namespace aqua_interfaces
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct CleanWall_SendGoal_Response_
{
  using Type = CleanWall_SendGoal_Response_<ContainerAllocator>;

  explicit CleanWall_SendGoal_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : stamp(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->accepted = false;
    }
  }

  explicit CleanWall_SendGoal_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : stamp(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->accepted = false;
    }
  }

  // field types and members
  using _accepted_type =
    bool;
  _accepted_type accepted;
  using _stamp_type =
    builtin_interfaces::msg::Time_<ContainerAllocator>;
  _stamp_type stamp;

  // setters for named parameter idiom
  Type & set__accepted(
    const bool & _arg)
  {
    this->accepted = _arg;
    return *this;
  }
  Type & set__stamp(
    const builtin_interfaces::msg::Time_<ContainerAllocator> & _arg)
  {
    this->stamp = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    aqua_interfaces::action::CleanWall_SendGoal_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const aqua_interfaces::action::CleanWall_SendGoal_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_SendGoal_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_SendGoal_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_SendGoal_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_SendGoal_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_SendGoal_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_SendGoal_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_SendGoal_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_SendGoal_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_SendGoal_Response
    std::shared_ptr<aqua_interfaces::action::CleanWall_SendGoal_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_SendGoal_Response
    std::shared_ptr<aqua_interfaces::action::CleanWall_SendGoal_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const CleanWall_SendGoal_Response_ & other) const
  {
    if (this->accepted != other.accepted) {
      return false;
    }
    if (this->stamp != other.stamp) {
      return false;
    }
    return true;
  }
  bool operator!=(const CleanWall_SendGoal_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct CleanWall_SendGoal_Response_

// alias to use template instance with default allocator
using CleanWall_SendGoal_Response =
  aqua_interfaces::action::CleanWall_SendGoal_Response_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace aqua_interfaces

namespace aqua_interfaces
{

namespace action
{

struct CleanWall_SendGoal
{
  using Request = aqua_interfaces::action::CleanWall_SendGoal_Request;
  using Response = aqua_interfaces::action::CleanWall_SendGoal_Response;
};

}  // namespace action

}  // namespace aqua_interfaces


// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__aqua_interfaces__action__CleanWall_GetResult_Request __attribute__((deprecated))
#else
# define DEPRECATED__aqua_interfaces__action__CleanWall_GetResult_Request __declspec(deprecated)
#endif

namespace aqua_interfaces
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct CleanWall_GetResult_Request_
{
  using Type = CleanWall_GetResult_Request_<ContainerAllocator>;

  explicit CleanWall_GetResult_Request_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_init)
  {
    (void)_init;
  }

  explicit CleanWall_GetResult_Request_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _goal_id_type =
    unique_identifier_msgs::msg::UUID_<ContainerAllocator>;
  _goal_id_type goal_id;

  // setters for named parameter idiom
  Type & set__goal_id(
    const unique_identifier_msgs::msg::UUID_<ContainerAllocator> & _arg)
  {
    this->goal_id = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    aqua_interfaces::action::CleanWall_GetResult_Request_<ContainerAllocator> *;
  using ConstRawPtr =
    const aqua_interfaces::action::CleanWall_GetResult_Request_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_GetResult_Request_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_GetResult_Request_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_GetResult_Request_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_GetResult_Request_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_GetResult_Request_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_GetResult_Request_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_GetResult_Request_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_GetResult_Request_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_GetResult_Request
    std::shared_ptr<aqua_interfaces::action::CleanWall_GetResult_Request_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_GetResult_Request
    std::shared_ptr<aqua_interfaces::action::CleanWall_GetResult_Request_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const CleanWall_GetResult_Request_ & other) const
  {
    if (this->goal_id != other.goal_id) {
      return false;
    }
    return true;
  }
  bool operator!=(const CleanWall_GetResult_Request_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct CleanWall_GetResult_Request_

// alias to use template instance with default allocator
using CleanWall_GetResult_Request =
  aqua_interfaces::action::CleanWall_GetResult_Request_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace aqua_interfaces


// Include directives for member types
// Member 'result'
// already included above
// #include "aqua_interfaces/action/detail/clean_wall__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__aqua_interfaces__action__CleanWall_GetResult_Response __attribute__((deprecated))
#else
# define DEPRECATED__aqua_interfaces__action__CleanWall_GetResult_Response __declspec(deprecated)
#endif

namespace aqua_interfaces
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct CleanWall_GetResult_Response_
{
  using Type = CleanWall_GetResult_Response_<ContainerAllocator>;

  explicit CleanWall_GetResult_Response_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : result(_init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->status = 0;
    }
  }

  explicit CleanWall_GetResult_Response_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : result(_alloc, _init)
  {
    if (rosidl_runtime_cpp::MessageInitialization::ALL == _init ||
      rosidl_runtime_cpp::MessageInitialization::ZERO == _init)
    {
      this->status = 0;
    }
  }

  // field types and members
  using _status_type =
    int8_t;
  _status_type status;
  using _result_type =
    aqua_interfaces::action::CleanWall_Result_<ContainerAllocator>;
  _result_type result;

  // setters for named parameter idiom
  Type & set__status(
    const int8_t & _arg)
  {
    this->status = _arg;
    return *this;
  }
  Type & set__result(
    const aqua_interfaces::action::CleanWall_Result_<ContainerAllocator> & _arg)
  {
    this->result = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    aqua_interfaces::action::CleanWall_GetResult_Response_<ContainerAllocator> *;
  using ConstRawPtr =
    const aqua_interfaces::action::CleanWall_GetResult_Response_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_GetResult_Response_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_GetResult_Response_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_GetResult_Response_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_GetResult_Response_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_GetResult_Response_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_GetResult_Response_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_GetResult_Response_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_GetResult_Response_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_GetResult_Response
    std::shared_ptr<aqua_interfaces::action::CleanWall_GetResult_Response_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_GetResult_Response
    std::shared_ptr<aqua_interfaces::action::CleanWall_GetResult_Response_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const CleanWall_GetResult_Response_ & other) const
  {
    if (this->status != other.status) {
      return false;
    }
    if (this->result != other.result) {
      return false;
    }
    return true;
  }
  bool operator!=(const CleanWall_GetResult_Response_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct CleanWall_GetResult_Response_

// alias to use template instance with default allocator
using CleanWall_GetResult_Response =
  aqua_interfaces::action::CleanWall_GetResult_Response_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace aqua_interfaces

namespace aqua_interfaces
{

namespace action
{

struct CleanWall_GetResult
{
  using Request = aqua_interfaces::action::CleanWall_GetResult_Request;
  using Response = aqua_interfaces::action::CleanWall_GetResult_Response;
};

}  // namespace action

}  // namespace aqua_interfaces


// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__struct.hpp"
// Member 'feedback'
// already included above
// #include "aqua_interfaces/action/detail/clean_wall__struct.hpp"

#ifndef _WIN32
# define DEPRECATED__aqua_interfaces__action__CleanWall_FeedbackMessage __attribute__((deprecated))
#else
# define DEPRECATED__aqua_interfaces__action__CleanWall_FeedbackMessage __declspec(deprecated)
#endif

namespace aqua_interfaces
{

namespace action
{

// message struct
template<class ContainerAllocator>
struct CleanWall_FeedbackMessage_
{
  using Type = CleanWall_FeedbackMessage_<ContainerAllocator>;

  explicit CleanWall_FeedbackMessage_(rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_init),
    feedback(_init)
  {
    (void)_init;
  }

  explicit CleanWall_FeedbackMessage_(const ContainerAllocator & _alloc, rosidl_runtime_cpp::MessageInitialization _init = rosidl_runtime_cpp::MessageInitialization::ALL)
  : goal_id(_alloc, _init),
    feedback(_alloc, _init)
  {
    (void)_init;
  }

  // field types and members
  using _goal_id_type =
    unique_identifier_msgs::msg::UUID_<ContainerAllocator>;
  _goal_id_type goal_id;
  using _feedback_type =
    aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator>;
  _feedback_type feedback;

  // setters for named parameter idiom
  Type & set__goal_id(
    const unique_identifier_msgs::msg::UUID_<ContainerAllocator> & _arg)
  {
    this->goal_id = _arg;
    return *this;
  }
  Type & set__feedback(
    const aqua_interfaces::action::CleanWall_Feedback_<ContainerAllocator> & _arg)
  {
    this->feedback = _arg;
    return *this;
  }

  // constant declarations

  // pointer types
  using RawPtr =
    aqua_interfaces::action::CleanWall_FeedbackMessage_<ContainerAllocator> *;
  using ConstRawPtr =
    const aqua_interfaces::action::CleanWall_FeedbackMessage_<ContainerAllocator> *;
  using SharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_FeedbackMessage_<ContainerAllocator>>;
  using ConstSharedPtr =
    std::shared_ptr<aqua_interfaces::action::CleanWall_FeedbackMessage_<ContainerAllocator> const>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_FeedbackMessage_<ContainerAllocator>>>
  using UniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_FeedbackMessage_<ContainerAllocator>, Deleter>;

  using UniquePtr = UniquePtrWithDeleter<>;

  template<typename Deleter = std::default_delete<
      aqua_interfaces::action::CleanWall_FeedbackMessage_<ContainerAllocator>>>
  using ConstUniquePtrWithDeleter =
    std::unique_ptr<aqua_interfaces::action::CleanWall_FeedbackMessage_<ContainerAllocator> const, Deleter>;
  using ConstUniquePtr = ConstUniquePtrWithDeleter<>;

  using WeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_FeedbackMessage_<ContainerAllocator>>;
  using ConstWeakPtr =
    std::weak_ptr<aqua_interfaces::action::CleanWall_FeedbackMessage_<ContainerAllocator> const>;

  // pointer types similar to ROS 1, use SharedPtr / ConstSharedPtr instead
  // NOTE: Can't use 'using' here because GNU C++ can't parse attributes properly
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_FeedbackMessage
    std::shared_ptr<aqua_interfaces::action::CleanWall_FeedbackMessage_<ContainerAllocator>>
    Ptr;
  typedef DEPRECATED__aqua_interfaces__action__CleanWall_FeedbackMessage
    std::shared_ptr<aqua_interfaces::action::CleanWall_FeedbackMessage_<ContainerAllocator> const>
    ConstPtr;

  // comparison operators
  bool operator==(const CleanWall_FeedbackMessage_ & other) const
  {
    if (this->goal_id != other.goal_id) {
      return false;
    }
    if (this->feedback != other.feedback) {
      return false;
    }
    return true;
  }
  bool operator!=(const CleanWall_FeedbackMessage_ & other) const
  {
    return !this->operator==(other);
  }
};  // struct CleanWall_FeedbackMessage_

// alias to use template instance with default allocator
using CleanWall_FeedbackMessage =
  aqua_interfaces::action::CleanWall_FeedbackMessage_<std::allocator<void>>;

// constant definitions

}  // namespace action

}  // namespace aqua_interfaces

#include "action_msgs/srv/cancel_goal.hpp"
#include "action_msgs/msg/goal_info.hpp"
#include "action_msgs/msg/goal_status_array.hpp"

namespace aqua_interfaces
{

namespace action
{

struct CleanWall
{
  /// The goal message defined in the action definition.
  using Goal = aqua_interfaces::action::CleanWall_Goal;
  /// The result message defined in the action definition.
  using Result = aqua_interfaces::action::CleanWall_Result;
  /// The feedback message defined in the action definition.
  using Feedback = aqua_interfaces::action::CleanWall_Feedback;

  struct Impl
  {
    /// The send_goal service using a wrapped version of the goal message as a request.
    using SendGoalService = aqua_interfaces::action::CleanWall_SendGoal;
    /// The get_result service using a wrapped version of the result message as a response.
    using GetResultService = aqua_interfaces::action::CleanWall_GetResult;
    /// The feedback message with generic fields which wraps the feedback message.
    using FeedbackMessage = aqua_interfaces::action::CleanWall_FeedbackMessage;

    /// The generic service to cancel a goal.
    using CancelGoalService = action_msgs::srv::CancelGoal;
    /// The generic message for the status of a goal.
    using GoalStatusMessage = action_msgs::msg::GoalStatusArray;
  };
};

typedef struct CleanWall CleanWall;

}  // namespace action

}  // namespace aqua_interfaces

#endif  // AQUA_INTERFACES__ACTION__DETAIL__CLEAN_WALL__STRUCT_HPP_
