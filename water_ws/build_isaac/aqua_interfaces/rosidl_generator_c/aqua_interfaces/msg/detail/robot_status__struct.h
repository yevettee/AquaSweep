// generated from rosidl_generator_c/resource/idl__struct.h.em
// with input from aqua_interfaces:msg/RobotStatus.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__MSG__DETAIL__ROBOT_STATUS__STRUCT_H_
#define AQUA_INTERFACES__MSG__DETAIL__ROBOT_STATUS__STRUCT_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>


// Constants defined in the message

/// Constant 'IDLE'.
enum
{
  aqua_interfaces__msg__RobotStatus__IDLE = 0
};

/// Constant 'RUNNING'.
enum
{
  aqua_interfaces__msg__RobotStatus__RUNNING = 1
};

/// Constant 'PAUSED'.
enum
{
  aqua_interfaces__msg__RobotStatus__PAUSED = 2
};

/// Constant 'DISCHARGED'.
enum
{
  aqua_interfaces__msg__RobotStatus__DISCHARGED = 3
};

/// Struct defined in msg/RobotStatus in the package aqua_interfaces.
typedef struct aqua_interfaces__msg__RobotStatus
{
  uint8_t state;
  float battery_level;
  float collision_force;
} aqua_interfaces__msg__RobotStatus;

// Struct for a sequence of aqua_interfaces__msg__RobotStatus.
typedef struct aqua_interfaces__msg__RobotStatus__Sequence
{
  aqua_interfaces__msg__RobotStatus * data;
  /// The number of valid items in data
  size_t size;
  /// The number of allocated items in data
  size_t capacity;
} aqua_interfaces__msg__RobotStatus__Sequence;

#ifdef __cplusplus
}
#endif

#endif  // AQUA_INTERFACES__MSG__DETAIL__ROBOT_STATUS__STRUCT_H_
