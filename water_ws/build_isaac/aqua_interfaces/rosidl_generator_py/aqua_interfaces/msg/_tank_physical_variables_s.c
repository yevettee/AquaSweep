// generated from rosidl_generator_py/resource/_idl_support.c.em
// with input from aqua_interfaces:msg/TankPhysicalVariables.idl
// generated code does not contain a copyright notice
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#include <Python.h>
#include <stdbool.h>
#ifndef _WIN32
# pragma GCC diagnostic push
# pragma GCC diagnostic ignored "-Wunused-function"
#endif
#include "numpy/ndarrayobject.h"
#ifndef _WIN32
# pragma GCC diagnostic pop
#endif
#include "rosidl_runtime_c/visibility_control.h"
#include "aqua_interfaces/msg/detail/tank_physical_variables__struct.h"
#include "aqua_interfaces/msg/detail/tank_physical_variables__functions.h"


ROSIDL_GENERATOR_C_EXPORT
bool aqua_interfaces__msg__tank_physical_variables__convert_from_py(PyObject * _pymsg, void * _ros_message)
{
  // check that the passed message is of the expected Python class
  {
    char full_classname_dest[67];
    {
      char * class_name = NULL;
      char * module_name = NULL;
      {
        PyObject * class_attr = PyObject_GetAttrString(_pymsg, "__class__");
        if (class_attr) {
          PyObject * name_attr = PyObject_GetAttrString(class_attr, "__name__");
          if (name_attr) {
            class_name = (char *)PyUnicode_1BYTE_DATA(name_attr);
            Py_DECREF(name_attr);
          }
          PyObject * module_attr = PyObject_GetAttrString(class_attr, "__module__");
          if (module_attr) {
            module_name = (char *)PyUnicode_1BYTE_DATA(module_attr);
            Py_DECREF(module_attr);
          }
          Py_DECREF(class_attr);
        }
      }
      if (!class_name || !module_name) {
        return false;
      }
      snprintf(full_classname_dest, sizeof(full_classname_dest), "%s.%s", module_name, class_name);
    }
    assert(strncmp("aqua_interfaces.msg._tank_physical_variables.TankPhysicalVariables", full_classname_dest, 66) == 0);
  }
  aqua_interfaces__msg__TankPhysicalVariables * ros_message = _ros_message;
  {  // buoyancy
    PyObject * field = PyObject_GetAttrString(_pymsg, "buoyancy");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->buoyancy = (float)PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // drag
    PyObject * field = PyObject_GetAttrString(_pymsg, "drag");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->drag = (float)PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // lift
    PyObject * field = PyObject_GetAttrString(_pymsg, "lift");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->lift = (float)PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }
  {  // viscosity
    PyObject * field = PyObject_GetAttrString(_pymsg, "viscosity");
    if (!field) {
      return false;
    }
    assert(PyFloat_Check(field));
    ros_message->viscosity = (float)PyFloat_AS_DOUBLE(field);
    Py_DECREF(field);
  }

  return true;
}

ROSIDL_GENERATOR_C_EXPORT
PyObject * aqua_interfaces__msg__tank_physical_variables__convert_to_py(void * raw_ros_message)
{
  /* NOTE(esteve): Call constructor of TankPhysicalVariables */
  PyObject * _pymessage = NULL;
  {
    PyObject * pymessage_module = PyImport_ImportModule("aqua_interfaces.msg._tank_physical_variables");
    assert(pymessage_module);
    PyObject * pymessage_class = PyObject_GetAttrString(pymessage_module, "TankPhysicalVariables");
    assert(pymessage_class);
    Py_DECREF(pymessage_module);
    _pymessage = PyObject_CallObject(pymessage_class, NULL);
    Py_DECREF(pymessage_class);
    if (!_pymessage) {
      return NULL;
    }
  }
  aqua_interfaces__msg__TankPhysicalVariables * ros_message = (aqua_interfaces__msg__TankPhysicalVariables *)raw_ros_message;
  {  // buoyancy
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->buoyancy);
    {
      int rc = PyObject_SetAttrString(_pymessage, "buoyancy", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // drag
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->drag);
    {
      int rc = PyObject_SetAttrString(_pymessage, "drag", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // lift
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->lift);
    {
      int rc = PyObject_SetAttrString(_pymessage, "lift", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }
  {  // viscosity
    PyObject * field = NULL;
    field = PyFloat_FromDouble(ros_message->viscosity);
    {
      int rc = PyObject_SetAttrString(_pymessage, "viscosity", field);
      Py_DECREF(field);
      if (rc) {
        return NULL;
      }
    }
  }

  // ownership of _pymessage is transferred to the caller
  return _pymessage;
}
