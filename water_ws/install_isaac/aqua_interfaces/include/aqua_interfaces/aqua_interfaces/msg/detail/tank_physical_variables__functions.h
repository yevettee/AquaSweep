// generated from rosidl_generator_c/resource/idl__functions.h.em
// with input from aqua_interfaces:msg/TankPhysicalVariables.idl
// generated code does not contain a copyright notice

#ifndef AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__FUNCTIONS_H_
#define AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__FUNCTIONS_H_

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdbool.h>
#include <stdlib.h>

#include "rosidl_runtime_c/visibility_control.h"
#include "aqua_interfaces/msg/rosidl_generator_c__visibility_control.h"

#include "aqua_interfaces/msg/detail/tank_physical_variables__struct.h"

/// Initialize msg/TankPhysicalVariables message.
/**
 * If the init function is called twice for the same message without
 * calling fini inbetween previously allocated memory will be leaked.
 * \param[in,out] msg The previously allocated message pointer.
 * Fields without a default value will not be initialized by this function.
 * You might want to call memset(msg, 0, sizeof(
 * aqua_interfaces__msg__TankPhysicalVariables
 * )) before or use
 * aqua_interfaces__msg__TankPhysicalVariables__create()
 * to allocate and initialize the message.
 * \return true if initialization was successful, otherwise false
 */
ROSIDL_GENERATOR_C_PUBLIC_aqua_interfaces
bool
aqua_interfaces__msg__TankPhysicalVariables__init(aqua_interfaces__msg__TankPhysicalVariables * msg);

/// Finalize msg/TankPhysicalVariables message.
/**
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_aqua_interfaces
void
aqua_interfaces__msg__TankPhysicalVariables__fini(aqua_interfaces__msg__TankPhysicalVariables * msg);

/// Create msg/TankPhysicalVariables message.
/**
 * It allocates the memory for the message, sets the memory to zero, and
 * calls
 * aqua_interfaces__msg__TankPhysicalVariables__init().
 * \return The pointer to the initialized message if successful,
 * otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_aqua_interfaces
aqua_interfaces__msg__TankPhysicalVariables *
aqua_interfaces__msg__TankPhysicalVariables__create();

/// Destroy msg/TankPhysicalVariables message.
/**
 * It calls
 * aqua_interfaces__msg__TankPhysicalVariables__fini()
 * and frees the memory of the message.
 * \param[in,out] msg The allocated message pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_aqua_interfaces
void
aqua_interfaces__msg__TankPhysicalVariables__destroy(aqua_interfaces__msg__TankPhysicalVariables * msg);

/// Check for msg/TankPhysicalVariables message equality.
/**
 * \param[in] lhs The message on the left hand size of the equality operator.
 * \param[in] rhs The message on the right hand size of the equality operator.
 * \return true if messages are equal, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_aqua_interfaces
bool
aqua_interfaces__msg__TankPhysicalVariables__are_equal(const aqua_interfaces__msg__TankPhysicalVariables * lhs, const aqua_interfaces__msg__TankPhysicalVariables * rhs);

/// Copy a msg/TankPhysicalVariables message.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source message pointer.
 * \param[out] output The target message pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer is null
 *   or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_aqua_interfaces
bool
aqua_interfaces__msg__TankPhysicalVariables__copy(
  const aqua_interfaces__msg__TankPhysicalVariables * input,
  aqua_interfaces__msg__TankPhysicalVariables * output);

/// Initialize array of msg/TankPhysicalVariables messages.
/**
 * It allocates the memory for the number of elements and calls
 * aqua_interfaces__msg__TankPhysicalVariables__init()
 * for each element of the array.
 * \param[in,out] array The allocated array pointer.
 * \param[in] size The size / capacity of the array.
 * \return true if initialization was successful, otherwise false
 * If the array pointer is valid and the size is zero it is guaranteed
 # to return true.
 */
ROSIDL_GENERATOR_C_PUBLIC_aqua_interfaces
bool
aqua_interfaces__msg__TankPhysicalVariables__Sequence__init(aqua_interfaces__msg__TankPhysicalVariables__Sequence * array, size_t size);

/// Finalize array of msg/TankPhysicalVariables messages.
/**
 * It calls
 * aqua_interfaces__msg__TankPhysicalVariables__fini()
 * for each element of the array and frees the memory for the number of
 * elements.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_aqua_interfaces
void
aqua_interfaces__msg__TankPhysicalVariables__Sequence__fini(aqua_interfaces__msg__TankPhysicalVariables__Sequence * array);

/// Create array of msg/TankPhysicalVariables messages.
/**
 * It allocates the memory for the array and calls
 * aqua_interfaces__msg__TankPhysicalVariables__Sequence__init().
 * \param[in] size The size / capacity of the array.
 * \return The pointer to the initialized array if successful, otherwise NULL
 */
ROSIDL_GENERATOR_C_PUBLIC_aqua_interfaces
aqua_interfaces__msg__TankPhysicalVariables__Sequence *
aqua_interfaces__msg__TankPhysicalVariables__Sequence__create(size_t size);

/// Destroy array of msg/TankPhysicalVariables messages.
/**
 * It calls
 * aqua_interfaces__msg__TankPhysicalVariables__Sequence__fini()
 * on the array,
 * and frees the memory of the array.
 * \param[in,out] array The initialized array pointer.
 */
ROSIDL_GENERATOR_C_PUBLIC_aqua_interfaces
void
aqua_interfaces__msg__TankPhysicalVariables__Sequence__destroy(aqua_interfaces__msg__TankPhysicalVariables__Sequence * array);

/// Check for msg/TankPhysicalVariables message array equality.
/**
 * \param[in] lhs The message array on the left hand size of the equality operator.
 * \param[in] rhs The message array on the right hand size of the equality operator.
 * \return true if message arrays are equal in size and content, otherwise false.
 */
ROSIDL_GENERATOR_C_PUBLIC_aqua_interfaces
bool
aqua_interfaces__msg__TankPhysicalVariables__Sequence__are_equal(const aqua_interfaces__msg__TankPhysicalVariables__Sequence * lhs, const aqua_interfaces__msg__TankPhysicalVariables__Sequence * rhs);

/// Copy an array of msg/TankPhysicalVariables messages.
/**
 * This functions performs a deep copy, as opposed to the shallow copy that
 * plain assignment yields.
 *
 * \param[in] input The source array pointer.
 * \param[out] output The target array pointer, which must
 *   have been initialized before calling this function.
 * \return true if successful, or false if either pointer
 *   is null or memory allocation fails.
 */
ROSIDL_GENERATOR_C_PUBLIC_aqua_interfaces
bool
aqua_interfaces__msg__TankPhysicalVariables__Sequence__copy(
  const aqua_interfaces__msg__TankPhysicalVariables__Sequence * input,
  aqua_interfaces__msg__TankPhysicalVariables__Sequence * output);

#ifdef __cplusplus
}
#endif

#endif  // AQUA_INTERFACES__MSG__DETAIL__TANK_PHYSICAL_VARIABLES__FUNCTIONS_H_
