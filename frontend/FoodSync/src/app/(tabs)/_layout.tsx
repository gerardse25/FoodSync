import { Tabs } from "expo-router";
import { Settings, Users } from "lucide-react-native";
import React from "react";
import { Platform } from "react-native";

export default function TabLayout() {
  return (
    <Tabs
      screenOptions={{
        // for hide the default header
        headerShown: false,
        //tab colors
        tabBarActiveTintColor: "#10B981",
        tabBarInactiveTintColor: "#9CA3AF",
        //tab bar styles
        tabBarStyle: {
          backgroundColor: "#FFFFFF",
          borderTopColor: "#E5E7EB",
          borderTopWidth: 1,
          elevation: 0, 
          shadowOpacity: 0, 
          height: Platform.OS === "ios" ? 85 : 65,
          paddingBottom: Platform.OS === "ios" ? 25 : 10,
          paddingTop: 10,
        },
        // tab label styles
        tabBarLabelStyle: {
          fontSize: 11,
          fontWeight: "500",
          marginTop: 4,
        },
      }}
    >

      {/*Household*/}
      <Tabs.Screen
        name="household"
        options={{
          title: "Household",
          tabBarIcon: ({ color, focused }) => (
            <Users color={color} size={24} strokeWidth={focused ? 2.5 : 2} />
          ),
        }}
      />

      {/*Settings*/}
      <Tabs.Screen
        name="settings"
        options={{
          title: "Settings",
          tabBarIcon: ({ color, focused }) => (
            <Settings color={color} size={24} strokeWidth={focused ? 2.5 : 2} />
          ),
        }}
      />
    </Tabs>
  );
}
