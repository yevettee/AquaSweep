// generated from rosidl_generator_cpp/resource/idl__builder.hpp.em
// with input from aqua_interfaces:action/CleanWall.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__ACTION__DETAIL__CLEAN_WALL__BUILDER_HPP_
#define AQUA_INTERFACES__ACTION__DETAIL__CLEAN_WALL__BUILDER_HPP_

#include <algorithm>
#include <utility>

#include "aqua_interfaces/action/detail/clean_wall__struct.hpp"
#include "rosidl_runtime_cpp/message_initialization.hpp"


namespace aqua_interfaces
{

namespace action
{


}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::aqua_interfaces::action::CleanWall_Goal>()
{
  return ::aqua_interfaces::action::CleanWall_Goal(rosidl_runtime_cpp::MessageInitialization::ZERO);
}

}  // namespace aqua_interfaces


namespace aqua_interfaces
{

namespace action
{

namespace builder
{

class Init_CleanWall_Result_success
{
public:
  Init_CleanWall_Result_success()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::aqua_interfaces::action::CleanWall_Result success(::aqua_interfaces::action::CleanWall_Result::_success_type arg)
  {
    msg_.success = std::move(arg);
    return std::move(msg_);
  }

private:
  ::aqua_interfaces::action::CleanWall_Result msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::aqua_interfaces::action::CleanWall_Result>()
{
  return aqua_interfaces::action::builder::Init_CleanWall_Result_success();
}

}  // namespace aqua_interfaces


namespace aqua_interfaces
{

namespace action
{

namespace builder
{

class Init_CleanWall_Feedback_progress
{
public:
  Init_CleanWall_Feedback_progress()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::aqua_interfaces::action::CleanWall_Feedback progress(::aqua_interfaces::action::CleanWall_Feedback::_progress_type arg)
  {
    msg_.progress = std::move(arg);
    return std::move(msg_);
  }

private:
  ::aqua_interfaces::action::CleanWall_Feedback msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::aqua_interfaces::action::CleanWall_Feedback>()
{
  return aqua_interfaces::action::builder::Init_CleanWall_Feedback_progress();
}

}  // namespace aqua_interfaces


namespace aqua_interfaces
{

namespace action
{

namespace builder
{

class Init_CleanWall_SendGoal_Request_goal
{
public:
  explicit Init_CleanWall_SendGoal_Request_goal(::aqua_interfaces::action::CleanWall_SendGoal_Request & msg)
  : msg_(msg)
  {}
  ::aqua_interfaces::action::CleanWall_SendGoal_Request goal(::aqua_interfaces::action::CleanWall_SendGoal_Request::_goal_type arg)
  {
    msg_.goal = std::move(arg);
    return std::move(msg_);
  }

private:
  ::aqua_interfaces::action::CleanWall_SendGoal_Request msg_;
};

class Init_CleanWall_SendGoal_Request_goal_id
{
public:
  Init_CleanWall_SendGoal_Request_goal_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_CleanWall_SendGoal_Request_goal goal_id(::aqua_interfaces::action::CleanWall_SendGoal_Request::_goal_id_type arg)
  {
    msg_.goal_id = std::move(arg);
    return Init_CleanWall_SendGoal_Request_goal(msg_);
  }

private:
  ::aqua_interfaces::action::CleanWall_SendGoal_Request msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::aqua_interfaces::action::CleanWall_SendGoal_Request>()
{
  return aqua_interfaces::action::builder::Init_CleanWall_SendGoal_Request_goal_id();
}

}  // namespace aqua_interfaces


namespace aqua_interfaces
{

namespace action
{

namespace builder
{

class Init_CleanWall_SendGoal_Response_stamp
{
public:
  explicit Init_CleanWall_SendGoal_Response_stamp(::aqua_interfaces::action::CleanWall_SendGoal_Response & msg)
  : msg_(msg)
  {}
  ::aqua_interfaces::action::CleanWall_SendGoal_Response stamp(::aqua_interfaces::action::CleanWall_SendGoal_Response::_stamp_type arg)
  {
    msg_.stamp = std::move(arg);
    return std::move(msg_);
  }

private:
  ::aqua_interfaces::action::CleanWall_SendGoal_Response msg_;
};

class Init_CleanWall_SendGoal_Response_accepted
{
public:
  Init_CleanWall_SendGoal_Response_accepted()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_CleanWall_SendGoal_Response_stamp accepted(::aqua_interfaces::action::CleanWall_SendGoal_Response::_accepted_type arg)
  {
    msg_.accepted = std::move(arg);
    return Init_CleanWall_SendGoal_Response_stamp(msg_);
  }

private:
  ::aqua_interfaces::action::CleanWall_SendGoal_Response msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::aqua_interfaces::action::CleanWall_SendGoal_Response>()
{
  return aqua_interfaces::action::builder::Init_CleanWall_SendGoal_Response_accepted();
}

}  // namespace aqua_interfaces


namespace aqua_interfaces
{

namespace action
{

namespace builder
{

class Init_CleanWall_GetResult_Request_goal_id
{
public:
  Init_CleanWall_GetResult_Request_goal_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  ::aqua_interfaces::action::CleanWall_GetResult_Request goal_id(::aqua_interfaces::action::CleanWall_GetResult_Request::_goal_id_type arg)
  {
    msg_.goal_id = std::move(arg);
    return std::move(msg_);
  }

private:
  ::aqua_interfaces::action::CleanWall_GetResult_Request msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::aqua_interfaces::action::CleanWall_GetResult_Request>()
{
  return aqua_interfaces::action::builder::Init_CleanWall_GetResult_Request_goal_id();
}

}  // namespace aqua_interfaces


namespace aqua_interfaces
{

namespace action
{

namespace builder
{

class Init_CleanWall_GetResult_Response_result
{
public:
  explicit Init_CleanWall_GetResult_Response_result(::aqua_interfaces::action::CleanWall_GetResult_Response & msg)
  : msg_(msg)
  {}
  ::aqua_interfaces::action::CleanWall_GetResult_Response result(::aqua_interfaces::action::CleanWall_GetResult_Response::_result_type arg)
  {
    msg_.result = std::move(arg);
    return std::move(msg_);
  }

private:
  ::aqua_interfaces::action::CleanWall_GetResult_Response msg_;
};

class Init_CleanWall_GetResult_Response_status
{
public:
  Init_CleanWall_GetResult_Response_status()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_CleanWall_GetResult_Response_result status(::aqua_interfaces::action::CleanWall_GetResult_Response::_status_type arg)
  {
    msg_.status = std::move(arg);
    return Init_CleanWall_GetResult_Response_result(msg_);
  }

private:
  ::aqua_interfaces::action::CleanWall_GetResult_Response msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::aqua_interfaces::action::CleanWall_GetResult_Response>()
{
  return aqua_interfaces::action::builder::Init_CleanWall_GetResult_Response_status();
}

}  // namespace aqua_interfaces


namespace aqua_interfaces
{

namespace action
{

namespace builder
{

class Init_CleanWall_FeedbackMessage_feedback
{
public:
  explicit Init_CleanWall_FeedbackMessage_feedback(::aqua_interfaces::action::CleanWall_FeedbackMessage & msg)
  : msg_(msg)
  {}
  ::aqua_interfaces::action::CleanWall_FeedbackMessage feedback(::aqua_interfaces::action::CleanWall_FeedbackMessage::_feedback_type arg)
  {
    msg_.feedback = std::move(arg);
    return std::move(msg_);
  }

private:
  ::aqua_interfaces::action::CleanWall_FeedbackMessage msg_;
};

class Init_CleanWall_FeedbackMessage_goal_id
{
public:
  Init_CleanWall_FeedbackMessage_goal_id()
  : msg_(::rosidl_runtime_cpp::MessageInitialization::SKIP)
  {}
  Init_CleanWall_FeedbackMessage_feedback goal_id(::aqua_interfaces::action::CleanWall_FeedbackMessage::_goal_id_type arg)
  {
    msg_.goal_id = std::move(arg);
    return Init_CleanWall_FeedbackMessage_feedback(msg_);
  }

private:
  ::aqua_interfaces::action::CleanWall_FeedbackMessage msg_;
};

}  // namespace builder

}  // namespace action

template<typename MessageType>
auto build();

template<>
inline
auto build<::aqua_interfaces::action::CleanWall_FeedbackMessage>()
{
  return aqua_interfaces::action::builder::Init_CleanWall_FeedbackMessage_goal_id();
}

}  // namespace aqua_interfaces

#endif  // AQUA_INTERFACES__ACTION__DETAIL__CLEAN_WALL__BUILDER_HPP_
