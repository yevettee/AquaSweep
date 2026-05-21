// generated from rosidl_generator_c/resource/idl__functions.c.em
// with input from aqua_interfaces:msg/TankPhysicalVariables.idl
// generated code does not contain a copyright notice
#include "aqua_interfaces/msg/detail/tank_physical_variables__functions.h"

#include <assert.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>

#include "rcutils/allocator.h"


bool
aqua_interfaces__msg__TankPhysicalVariables__init(aqua_interfaces__msg__TankPhysicalVariables * msg)
{
  if (!msg) {
    return false;
  }
  // buoyancy
  // drag
  // lift
  // viscosity
  return true;
}

void
aqua_interfaces__msg__TankPhysicalVariables__fini(aqua_interfaces__msg__TankPhysicalVariables * msg)
{
  if (!msg) {
    return;
  }
  // buoyancy
  // drag
  // lift
  // viscosity
}

bool
aqua_interfaces__msg__TankPhysicalVariables__are_equal(const aqua_interfaces__msg__TankPhysicalVariables * lhs, const aqua_interfaces__msg__TankPhysicalVariables * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  // buoyancy
  if (lhs->buoyancy != rhs->buoyancy) {
    return false;
  }
  // drag
  if (lhs->drag != rhs->drag) {
    return false;
  }
  // lift
  if (lhs->lift != rhs->lift) {
    return false;
  }
  // viscosity
  if (lhs->viscosity != rhs->viscosity) {
    return false;
  }
  return true;
}

bool
aqua_interfaces__msg__TankPhysicalVariables__copy(
  const aqua_interfaces__msg__TankPhysicalVariables * input,
  aqua_interfaces__msg__TankPhysicalVariables * output)
{
  if (!input || !output) {
    return false;
  }
  // buoyancy
  output->buoyancy = input->buoyancy;
  // drag
  output->drag = input->drag;
  // lift
  output->lift = input->lift;
  // viscosity
  output->viscosity = input->viscosity;
  return true;
}

aqua_interfaces__msg__TankPhysicalVariables *
aqua_interfaces__msg__TankPhysicalVariables__create()
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  aqua_interfaces__msg__TankPhysicalVariables * msg = (aqua_interfaces__msg__TankPhysicalVariables *)allocator.allocate(sizeof(aqua_interfaces__msg__TankPhysicalVariables), allocator.state);
  if (!msg) {
    return NULL;
  }
  memset(msg, 0, sizeof(aqua_interfaces__msg__TankPhysicalVariables));
  bool success = aqua_interfaces__msg__TankPhysicalVariables__init(msg);
  if (!success) {
    allocator.deallocate(msg, allocator.state);
    return NULL;
  }
  return msg;
}

void
aqua_interfaces__msg__TankPhysicalVariables__destroy(aqua_interfaces__msg__TankPhysicalVariables * msg)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (msg) {
    aqua_interfaces__msg__TankPhysicalVariables__fini(msg);
  }
  allocator.deallocate(msg, allocator.state);
}


bool
aqua_interfaces__msg__TankPhysicalVariables__Sequence__init(aqua_interfaces__msg__TankPhysicalVariables__Sequence * array, size_t size)
{
  if (!array) {
    return false;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  aqua_interfaces__msg__TankPhysicalVariables * data = NULL;

  if (size) {
    data = (aqua_interfaces__msg__TankPhysicalVariables *)allocator.zero_allocate(size, sizeof(aqua_interfaces__msg__TankPhysicalVariables), allocator.state);
    if (!data) {
      return false;
    }
    // initialize all array elements
    size_t i;
    for (i = 0; i < size; ++i) {
      bool success = aqua_interfaces__msg__TankPhysicalVariables__init(&data[i]);
      if (!success) {
        break;
      }
    }
    if (i < size) {
      // if initialization failed finalize the already initialized array elements
      for (; i > 0; --i) {
        aqua_interfaces__msg__TankPhysicalVariables__fini(&data[i - 1]);
      }
      allocator.deallocate(data, allocator.state);
      return false;
    }
  }
  array->data = data;
  array->size = size;
  array->capacity = size;
  return true;
}

void
aqua_interfaces__msg__TankPhysicalVariables__Sequence__fini(aqua_interfaces__msg__TankPhysicalVariables__Sequence * array)
{
  if (!array) {
    return;
  }
  rcutils_allocator_t allocator = rcutils_get_default_allocator();

  if (array->data) {
    // ensure that data and capacity values are consistent
    assert(array->capacity > 0);
    // finalize all array elements
    for (size_t i = 0; i < array->capacity; ++i) {
      aqua_interfaces__msg__TankPhysicalVariables__fini(&array->data[i]);
    }
    allocator.deallocate(array->data, allocator.state);
    array->data = NULL;
    array->size = 0;
    array->capacity = 0;
  } else {
    // ensure that data, size, and capacity values are consistent
    assert(0 == array->size);
    assert(0 == array->capacity);
  }
}

aqua_interfaces__msg__TankPhysicalVariables__Sequence *
aqua_interfaces__msg__TankPhysicalVariables__Sequence__create(size_t size)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  aqua_interfaces__msg__TankPhysicalVariables__Sequence * array = (aqua_interfaces__msg__TankPhysicalVariables__Sequence *)allocator.allocate(sizeof(aqua_interfaces__msg__TankPhysicalVariables__Sequence), allocator.state);
  if (!array) {
    return NULL;
  }
  bool success = aqua_interfaces__msg__TankPhysicalVariables__Sequence__init(array, size);
  if (!success) {
    allocator.deallocate(array, allocator.state);
    return NULL;
  }
  return array;
}

void
aqua_interfaces__msg__TankPhysicalVariables__Sequence__destroy(aqua_interfaces__msg__TankPhysicalVariables__Sequence * array)
{
  rcutils_allocator_t allocator = rcutils_get_default_allocator();
  if (array) {
    aqua_interfaces__msg__TankPhysicalVariables__Sequence__fini(array);
  }
  allocator.deallocate(array, allocator.state);
}

bool
aqua_interfaces__msg__TankPhysicalVariables__Sequence__are_equal(const aqua_interfaces__msg__TankPhysicalVariables__Sequence * lhs, const aqua_interfaces__msg__TankPhysicalVariables__Sequence * rhs)
{
  if (!lhs || !rhs) {
    return false;
  }
  if (lhs->size != rhs->size) {
    return false;
  }
  for (size_t i = 0; i < lhs->size; ++i) {
    if (!aqua_interfaces__msg__TankPhysicalVariables__are_equal(&(lhs->data[i]), &(rhs->data[i]))) {
      return false;
    }
  }
  return true;
}

bool
aqua_interfaces__msg__TankPhysicalVariables__Sequence__copy(
  const aqua_interfaces__msg__TankPhysicalVariables__Sequence * input,
  aqua_interfaces__msg__TankPhysicalVariables__Sequence * output)
{
  if (!input || !output) {
    return false;
  }
  if (output->capacity < input->size) {
    const size_t allocation_size =
      input->size * sizeof(aqua_interfaces__msg__TankPhysicalVariables);
    rcutils_allocator_t allocator = rcutils_get_default_allocator();
    aqua_interfaces__msg__TankPhysicalVariables * data =
      (aqua_interfaces__msg__TankPhysicalVariables *)allocator.reallocate(
      output->data, allocation_size, allocator.state);
    if (!data) {
      return false;
    }
    // If reallocation succeeded, memory may or may not have been moved
    // to fulfill the allocation request, invalidating output->data.
    output->data = data;
    for (size_t i = output->capacity; i < input->size; ++i) {
      if (!aqua_interfaces__msg__TankPhysicalVariables__init(&output->data[i])) {
        // If initialization of any new item fails, roll back
        // all previously initialized items. Existing items
        // in output are to be left unmodified.
        for (; i-- > output->capacity; ) {
          aqua_interfaces__msg__TankPhysicalVariables__fini(&output->data[i]);
        }
        return false;
      }
    }
    output->capacity = input->size;
  }
  output->size = input->size;
  for (size_t i = 0; i < input->size; ++i) {
    if (!aqua_interfaces__msg__TankPhysicalVariables__copy(
        &(input->data[i]), &(output->data[i])))
    {
      return false;
    }
  }
  return true;
}
