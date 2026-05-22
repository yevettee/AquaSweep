#[cfg(feature = "serde")]
use serde::{Deserialize, Serialize};



// Corresponds to aqua_interfaces__msg__RobotStatus

// This struct is not documented.
#[allow(missing_docs)]

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct RobotStatus {

    // This member is not documented.
    #[allow(missing_docs)]
    pub state: u8,


    // This member is not documented.
    #[allow(missing_docs)]
    pub battery_level: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub collision_force: f32,

}

impl RobotStatus {

    // This constant is not documented.
    #[allow(missing_docs)]
    pub const IDLE: u8 = 0;


    // This constant is not documented.
    #[allow(missing_docs)]
    pub const RUNNING: u8 = 1;


    // This constant is not documented.
    #[allow(missing_docs)]
    pub const PAUSED: u8 = 2;


    // This constant is not documented.
    #[allow(missing_docs)]
    pub const DISCHARGED: u8 = 3;

}


impl Default for RobotStatus {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::RobotStatus::default())
  }
}

impl rosidl_runtime_rs::Message for RobotStatus {
  type RmwMsg = super::msg::rmw::RobotStatus;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        state: msg.state,
        battery_level: msg.battery_level,
        collision_force: msg.collision_force,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      state: msg.state,
      battery_level: msg.battery_level,
      collision_force: msg.collision_force,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      state: msg.state,
      battery_level: msg.battery_level,
      collision_force: msg.collision_force,
    }
  }
}


// Corresponds to aqua_interfaces__msg__PoolStatus

// This struct is not documented.
#[allow(missing_docs)]

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct PoolStatus {

    // This member is not documented.
    #[allow(missing_docs)]
    pub pollution_level: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub fish_type: std::string::String,


    // This member is not documented.
    #[allow(missing_docs)]
    pub fish_count: i32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub fish_count_suspicious: i32,

}



impl Default for PoolStatus {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::PoolStatus::default())
  }
}

impl rosidl_runtime_rs::Message for PoolStatus {
  type RmwMsg = super::msg::rmw::PoolStatus;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        pollution_level: msg.pollution_level,
        fish_type: msg.fish_type.as_str().into(),
        fish_count: msg.fish_count,
        fish_count_suspicious: msg.fish_count_suspicious,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      pollution_level: msg.pollution_level,
        fish_type: msg.fish_type.as_str().into(),
      fish_count: msg.fish_count,
      fish_count_suspicious: msg.fish_count_suspicious,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      pollution_level: msg.pollution_level,
      fish_type: msg.fish_type.to_string(),
      fish_count: msg.fish_count,
      fish_count_suspicious: msg.fish_count_suspicious,
    }
  }
}


// Corresponds to aqua_interfaces__msg__PoolPhysicalVariables

// This struct is not documented.
#[allow(missing_docs)]

#[cfg_attr(feature = "serde", derive(Deserialize, Serialize))]
#[derive(Clone, Debug, PartialEq, PartialOrd)]
pub struct PoolPhysicalVariables {

    // This member is not documented.
    #[allow(missing_docs)]
    pub buoyancy: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub drag: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub lift: f32,


    // This member is not documented.
    #[allow(missing_docs)]
    pub viscosity: f32,

}



impl Default for PoolPhysicalVariables {
  fn default() -> Self {
    <Self as rosidl_runtime_rs::Message>::from_rmw_message(super::msg::rmw::PoolPhysicalVariables::default())
  }
}

impl rosidl_runtime_rs::Message for PoolPhysicalVariables {
  type RmwMsg = super::msg::rmw::PoolPhysicalVariables;

  fn into_rmw_message(msg_cow: std::borrow::Cow<'_, Self>) -> std::borrow::Cow<'_, Self::RmwMsg> {
    match msg_cow {
      std::borrow::Cow::Owned(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
        buoyancy: msg.buoyancy,
        drag: msg.drag,
        lift: msg.lift,
        viscosity: msg.viscosity,
      }),
      std::borrow::Cow::Borrowed(msg) => std::borrow::Cow::Owned(Self::RmwMsg {
      buoyancy: msg.buoyancy,
      drag: msg.drag,
      lift: msg.lift,
      viscosity: msg.viscosity,
      })
    }
  }

  fn from_rmw_message(msg: Self::RmwMsg) -> Self {
    Self {
      buoyancy: msg.buoyancy,
      drag: msg.drag,
      lift: msg.lift,
      viscosity: msg.viscosity,
    }
  }
}


