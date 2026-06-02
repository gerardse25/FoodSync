import { router, useFocusEffect } from "expo-router";
import {
  AlertCircle,
  Bell,
  Camera,
  ChevronRight,
  Package,
  Plus,
  ScanBarcode,
} from "lucide-react-native";
import React, { useCallback, useState } from "react";
import {
  BackHandler,
  Image,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { inventoryService } from "../../services/inventoryService";
import { notificationService } from "../../services/notificationService";

export default function Dashboard() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const [unreadCount, setUnreadCount] = useState(0);
  const [activeFilter, setActiveFilter] = useState<
    "expired" | "expiring_soon" | "ok"
  >("expired");

  const [expiredItems, setExpiredItems] = useState<any[]>([]);
  const [expiringItems, setExpiringItems] = useState<any[]>([]);
  const [okItems, setOkItems] = useState<any[]>([]);

  const [loading, setLoading] = useState(true);

  const loadDashboardData = async () => {
    try {
      setLoading(true);

      const [expired, expiring, ok] = await Promise.all([
        inventoryService.getInventoryProducts({ expiry_filter: "expired" }),
        inventoryService.getInventoryProducts({
          expiry_filter: "expiring_soon",
        }),
        inventoryService.getInventoryProducts({ expiry_filter: "ok" }),
      ]);

      setExpiredItems(expired);
      setExpiringItems(expiring);
      setOkItems(ok);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      loadDashboardData();
    }, []),
  );

  const getDaysLeft = (dateString?: string | null) => {
    if (!dateString) return 0;
    const parts = dateString.split("-");
    let expiry;
    if (parts.length === 3) {
      const [year, month, day] = parts.map(Number);
      expiry = new Date(year, month - 1, day, 0, 0, 0, 0);
    } else {
      expiry = new Date(dateString);
      expiry.setHours(0, 0, 0, 0);
    }
    return Math.round(
      (expiry.getTime() - today.getTime()) / (1000 * 60 * 60 * 24),
    );
  };

  const getDisplayedItems = () => {
    const sourceList =
      activeFilter === "expired"
        ? expiredItems
        : activeFilter === "expiring_soon"
          ? expiringItems
          : okItems;

    return sourceList.map((p) => ({
      id: p.id_producte,
      name: p.nom,
      brand: p.marca || "Sense marca",
      daysLeft: getDaysLeft(p.data_caducitat),
      image: p.imatge_url,
      color:
        activeFilter === "expired"
          ? "#FEF2F2"
          : activeFilter === "expiring_soon"
            ? "#FFFBEB"
            : "#F0FDF4",
    }));
  };

  const displayedItems = getDisplayedItems();

  const counts = {
    expired: expiredItems.length,
    expiring: expiringItems.length,
    ok: okItems.length,
  };

  useFocusEffect(
    useCallback(() => {
      const onBackPress = () => true;

      const subscription = BackHandler.addEventListener(
        "hardwareBackPress",
        onBackPress,
      );

      const fetchUnreadNotifications = async () => {
        try {
          const notifications = await notificationService.getNotifications();
          const unread = notifications.filter((n) => !n.is_read).length;
          setUnreadCount(unread);
        } catch (error) {
          console.error(
            "Error al carregar les notificacions al dashboard:",
            error,
          );
        }
      };

      fetchUnreadNotifications();

      return () => subscription.remove();
    }, []),
  );

  return (
    <SafeAreaView className="flex-1 bg-white">
      <View className="px-6 pt-6 pb-4 flex-row justify-between items-center border-b border-gray-200 bg-white">
        <View>
          <Text className="text-2xl font-bold text-gray-900">
            La meva nevera
          </Text>
          <Text className="text-sm text-gray-500 mt-1 capitalize">
            {today.toLocaleDateString("ca-ES", {
              weekday: "long",
              month: "long",
              day: "numeric",
            })}
          </Text>
        </View>

        <TouchableOpacity
          onPress={() => router.push("/notification")}
          className="p-2 relative bg-white border border-gray-100 rounded-xl"
        >
          <Bell color="#1F2937" size={24} />

          {unreadCount > 0 && (
            <View className="absolute -top-1 -right-1 bg-red-500 rounded-full min-w-[20px] h-5 px-1 items-center justify-center border-2 border-white">
              <Text className="text-white text-[10px] font-bold">
                {unreadCount > 99 ? "99+" : unreadCount}
              </Text>
            </View>
          )}
        </TouchableOpacity>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} className="flex-1">
        <View className="flex-row px-6 gap-3 mt-4">
          <TouchableOpacity
            onPress={() => setActiveFilter("expired")}
            className={`flex-1 p-4 rounded-3xl border ${activeFilter === "expired" ? "bg-red-100 border-red-200" : "bg-red-50 border-red-100"}`}
          >
            <Text className="text-2xl font-bold text-red-700">
              {counts.expired}
            </Text>
            <Text className="text-xs text-red-600 font-medium mt-1">
              Vençuts
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => setActiveFilter("expiring_soon")}
            className={`flex-1 p-4 rounded-3xl border ${activeFilter === "expiring_soon" ? "bg-amber-100 border-amber-200" : "bg-amber-50 border-amber-100"}`}
          >
            <Text className="text-2xl font-bold text-amber-700">
              {counts.expiring}
            </Text>
            <Text className="text-xs text-amber-600 font-medium mt-1">
              Caduquen aviat
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={() => setActiveFilter("ok")}
            className={`flex-1 p-4 rounded-3xl border ${activeFilter === "ok" ? "bg-emerald-100 border-emerald-200" : "bg-emerald-50 border-emerald-100"}`}
          >
            <Text className="text-2xl font-bold text-emerald-700">
              {counts.ok}
            </Text>
            <Text className="text-xs text-emerald-600 font-medium mt-1">
              Frescs
            </Text>
          </TouchableOpacity>
        </View>

        <View className="px-6 mt-8 flex-row gap-3">
          <TouchableOpacity
            className="flex-1 bg-emerald-500 p-4 rounded-3xl items-center"
            onPress={() => router.push("/products/scanReceipt")}
          >
            <Camera size={24} color="white" />
            <Text className="text-white text-[10px] font-bold mt-2 text-center">
              Tiquet
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            className="flex-1 bg-gray-100 p-4 rounded-3xl items-center"
            onPress={() => router.push("/products/scanBarcode")}
          >
            <ScanBarcode size={24} color="#10B981" />
            <Text className="text-gray-900 text-[10px] font-bold mt-2 text-center">
              Codi de barres
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            className="flex-1 bg-gray-50 p-4 rounded-3xl items-center border border-gray-100"
            onPress={() => router.push("/products/addManualProducts")}
          >
            <Plus size={24} color="#6B7280" />
            <Text className="text-gray-600 text-[10px] font-bold mt-2 text-center">
              Manual
            </Text>
          </TouchableOpacity>
        </View>

        <View className="px-6 mt-8 mb-8">
          <View className="flex-row justify-between items-center mb-4">
            <View className="flex-row items-center gap-2">
              <AlertCircle size={20} color="#F59E0B" />
              <Text className="text-lg font-bold text-gray-900 capitalize">
                {activeFilter === "expired"
                  ? "Productes vençuts"
                  : activeFilter === "expiring_soon"
                    ? "Caduquen aviat"
                    : "Productes frescos"}
              </Text>
            </View>

            <TouchableOpacity onPress={() => router.push("/inventory")}>
              <Text className="text-emerald-600 font-bold">Veure-ho tot</Text>
            </TouchableOpacity>
          </View>

          {displayedItems.length > 0 ? (
            displayedItems.map((item) => (
              <TouchableOpacity
                key={item.id}
                className="flex-row items-center p-3 rounded-2xl mb-3 border border-gray-100"
                style={{ backgroundColor: item.color }}
                onPress={() => router.push(`/product/${item.id}`)}
              >
                {item.image ? (
                  <Image
                    source={{ uri: item.image }}
                    className="w-14 h-14 rounded-xl bg-white"
                  />
                ) : (
                  <View className="w-14 h-14 rounded-xl bg-white items-center justify-center">
                    <Package size={24} color="#9CA3AF" />
                  </View>
                )}

                <View className="flex-1 ml-4">
                  <Text className="font-bold text-gray-900 text-base">
                    {item.name}
                  </Text>
                  <Text className="text-xs font-bold text-gray-600">
                    {activeFilter === "expired"
                      ? `Vençut fa ${Math.abs(item.daysLeft)} dies`
                      : `Queden ${item.daysLeft} dies`}
                  </Text>
                </View>
                <ChevronRight size={20} color="#9CA3AF" />
              </TouchableOpacity>
            ))
          ) : (
            <Text className="text-gray-500 text-center py-4">
              No s&apos;han trobat productes en aquesta categoria.
            </Text>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
