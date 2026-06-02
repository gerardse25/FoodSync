import { useFocusEffect } from "expo-router";
import React, { useCallback, useState } from "react";
import { ActivityIndicator } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import HouseholdDashboard from "../../components/household/HouseholdDashboard";
import NoHousehold from "../../components/household/NoHousehold";
import { useAuth } from "../../context/AuthContext";
import { homeService } from "../../services/homeService";

export default function HouseholdScreen() {
  const { session, setHasHome } = useAuth();
  const [currentHousehold, setCurrentHousehold] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useFocusEffect(
    useCallback(() => {
      fetchHomeData();
    }, []),
  );

  const fetchHomeData = async () => {
    setIsLoading(true);
    try {
      const data = await homeService.getHome();
      setCurrentHousehold(data);
      setHasHome(true);
    } catch (error: any) {
      setCurrentHousehold(null);
      setHasHome(false);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <SafeAreaView className="flex-1 bg-[#F8FAF8] justify-center items-center">
        <ActivityIndicator size="large" color="#10B981" />
      </SafeAreaView>
    );
  }

  if (!currentHousehold) {
    return <NoHousehold onSuccess={fetchHomeData} />;
  }

  return (
    <HouseholdDashboard
      household={currentHousehold}
      session={session}
      onRefresh={fetchHomeData}
    />
  );
}
