// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from aqua_interfaces:action/CleanWall.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__ACTION__DETAIL__CLEAN_WALL__STRUCT_H_
#define AQUA_INTERFACES__ACTION__DETAIL__CLEAN_WALL__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Struct defined in action/CleanWall in the package aqua_interfaces.
typedef struct aqua_interfaces__action__CleanWall_Goal
{
  uint8_t structure_needs_at_least_one_member;
} aqua_interfaces__action__CleanWall_Goal;

// Struct for a sequence of aqua_interfaces__action__CleanWall_Goal.
typedef struct aqua_interfaces__action__CleanWall_Goal__Sequence
{
  aqua_interfaces__action__CleanWall_Goal * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} aqua_interfaces__action__CleanWall_Goal__Sequence;


// Constants defined in the message

/// Struct defined in action/CleanWall in the package aqua_interfaces.
typedef struct aqua_interfaces__action__CleanWall_Result
{
  bool success;
} aqua_interfaces__action__CleanWall_Result;

// Struct for a sequence of aqua_interfaces__action__CleanWall_Result.
typedef struct aqua_interfaces__action__CleanWall_Result__Sequence
{
  aqua_interfaces__action__CleanWall_Result * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} aqua_interfaces__action__CleanWall_Result__Sequence;


// Constants defined in the message

/// Struct defined in action/CleanWall in the package aqua_interfaces.
typedef struct aqua_interfaces__action__CleanWall_Feedback
{
  float progress;
} aqua_interfaces__action__CleanWall_Feedback;

// Struct for a sequence of aqua_interfaces__action__CleanWall_Feedback.
typedef struct aqua_interfaces__action__CleanWall_Feedback__Sequence
{
  aqua_interfaces__action__CleanWall_Feedback * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} aqua_interfaces__action__CleanWall_Feedback__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'goal_id'
#include "unique_identifier_msgs/msg/detail/uuid__struct.h"
// Member 'goal'
#include "aqua_interfaces/action/detail/clean_wall__struct.h"

/// Struct defined in action/CleanWall in the package aqua_interfaces.
typedef struct aqua_interfaces__action__CleanWall_SendGoal_Request
{
  unique_identifier_msgs__msg__UUID goal_id;
  aqua_interfaces__action__CleanWall_Goal goal;
} aqua_interfaces__action__CleanWall_SendGoal_Request;

// Struct for a sequence of aqua_interfaces__action__CleanWall_SendGoal_Request.
typedef struct aqua_interfaces__action__CleanWall_SendGoal_Request__Sequence
{
  aqua_interfaces__action__CleanWall_SendGoal_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} aqua_interfaces__action__CleanWall_SendGoal_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'stamp'
#include "builtin_interfaces/msg/detail/time__struct.h"

/// Struct defined in action/CleanWall in the package aqua_interfaces.
typedef struct aqua_interfaces__action__CleanWall_SendGoal_Response
{
  bool accepted;
  builtin_interfaces__msg__Time stamp;
} aqua_interfaces__action__CleanWall_SendGoal_Response;

// Struct for a sequence of aqua_interfaces__action__CleanWall_SendGoal_Response.
typedef struct aqua_interfaces__action__CleanWall_SendGoal_Response__Sequence
{
  aqua_interfaces__action__CleanWall_SendGoal_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} aqua_interfaces__action__CleanWall_SendGoal_Response__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__struct.h"

/// Struct defined in action/CleanWall in the package aqua_interfaces.
typedef struct aqua_interfaces__action__CleanWall_GetResult_Request
{
  unique_identifier_msgs__msg__UUID goal_id;
} aqua_interfaces__action__CleanWall_GetResult_Request;

// Struct for a sequence of aqua_interfaces__action__CleanWall_GetResult_Request.
typedef struct aqua_interfaces__action__CleanWall_GetResult_Request__Sequence
{
  aqua_interfaces__action__CleanWall_GetResult_Request * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} aqua_interfaces__action__CleanWall_GetResult_Request__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'result'
// already included above
// #include "aqua_interfaces/action/detail/clean_wall__struct.h"

/// Struct defined in action/CleanWall in the package aqua_interfaces.
typedef struct aqua_interfaces__action__CleanWall_GetResult_Response
{
  int8_t status;
  aqua_interfaces__action__CleanWall_Result result;
} aqua_interfaces__action__CleanWall_GetResult_Response;

// Struct for a sequence of aqua_interfaces__action__CleanWall_GetResult_Response.
typedef struct aqua_interfaces__action__CleanWall_GetResult_Response__Sequence
{
  aqua_interfaces__action__CleanWall_GetResult_Response * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} aqua_interfaces__action__CleanWall_GetResult_Response__Sequence;


// Constants defined in the message

// Include directives for member types
// Member 'goal_id'
// already included above
// #include "unique_identifier_msgs/msg/detail/uuid__struct.h"
// Member 'feedback'
// already included above
// #include "aqua_interfaces/action/detail/clean_wall__struct.h"

/// Struct defined in action/CleanWall in the package aqua_interfaces.
typedef struct aqua_interfaces__action__CleanWall_FeedbackMessage
{
  unique_identifier_msgs__msg__UUID goal_id;
  aqua_interfaces__action__CleanWall_Feedback feedback;
} aqua_interfaces__action__CleanWall_FeedbackMessage;

// Struct for a sequence of aqua_interfaces__action__CleanWall_FeedbackMessage.
typedef struct aqua_interfaces__action__CleanWall_FeedbackMessage__Sequence
{
  aqua_interfaces__action__CleanWall_FeedbackMessage * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} aqua_interfaces__action__CleanWall_FeedbackMessage__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // AQUA_INTERFACES__ACTION__DETAIL__CLEAN_WALL__STRUCT_H_
