import { router } from "expo-router";
import {
  AlertTriangle,
  ArrowLeft,
  BellOff,
  Calendar,
  Info,
  Package,
  UserPlus
} from "lucide-react-native";
import React, { useEffect, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  RefreshControl,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import {
  NotificationItem,
  notificationService,
} from "../services/notificationService";

export default function NotificationsScreen() {
  const insets = useSafeAreaInsets();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState<"all" | "unread">("unread");

  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    try {
      const data = await notificationService.getNotifications();
      setNotifications(data);
    } catch (error) {
      console.error(error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    fetchNotifications();
  };

  const handleMarkAsRead = async (id: string, alreadyRead: boolean) => {
    if (alreadyRead) return;

    setNotifications((prev) =>
      prev.map((item) => (item.id === id ? { ...item, is_read: true } : item)),
    );

    try {
      await notificationService.markAsRead(id);
    } catch (error) {
      fetchNotifications();
    }
  };

  const filteredNotifications = notifications.filter((item) => {
    if (filter === "unread") return !item.is_read;
    return true;
  });

  const getNotificationIcon = (type: string, read: boolean) => {
    const baseClass =
      "w-11 h-11 rounded-full items-center justify-center mr-4 ";

    switch (type) {
      case "EXPIRED":
        return (
          <View className={`${baseClass} bg-red-50`}>
            <AlertTriangle color="#EF4444" size={20} />
          </View>
        );
      case "EXPIRING_SOON":
        return (
          <View className={`${baseClass} bg-amber-50`}>
            <Calendar color="#F59E0B" size={20} />
          </View>
        );
      case "HOME_MEMBER_JOINED": 
        return (
          <View className={`${baseClass} bg-emerald-50`}>
            <UserPlus color="#10B981" size={20} />
          </View>
        );
      case "HOME_PRODUCT_ADDED":
        return (
          <View className={`${baseClass} bg-blue-50`}>
            <Package color="#3B82F6" size={20} />
          </View>
        );
      default:
        return (
          <View className={`${baseClass} bg-gray-100`}>
            <Info color="#6B7280" size={20} />
          </View>
        );
    }
  };

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("ca-ES", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <View className="flex-1 bg-[#F8FAF8]">
      {/* Cabecera, respectant l'àrea segura superior */}
      <View
        className="bg-white border-b border-gray-100 px-4 flex-row items-center justify-between pb-4"
        style={{ paddingTop: Math.max(insets.top, 16) }}
      >
        <TouchableOpacity onPress={() => router.back()} className="p-2 -ml-2">
          <ArrowLeft color="#1F2937" size={24} />
        </TouchableOpacity>
        <Text className="text-xl font-bold text-gray-900">Notificacions</Text>
        <View className="w-10" />
      </View>

      {/* Selectors de Filtre ràpid */}
      <View className="flex-row px-6 py-4 gap-3 bg-white border-b border-gray-50">
        <TouchableOpacity
          className={`px-4 py-2 rounded-full flex-row items-center ${filter === "unread" ? "bg-emerald-500" : "bg-gray-100"}`}
          onPress={() => setFilter("unread")}
        >
          <Text
            className={`font-bold text-sm ${filter === "unread" ? "text-white" : "text-gray-600"}`}
          >
            No llegides
          </Text>
          {notifications.filter((n) => !n.is_read).length > 0 && (
            <View
              className={`ml-2 w-5 h-5 rounded-full items-center justify-center ${filter === "unread" ? "bg-white" : "bg-emerald-500"}`}
            >
              <Text
                className={`text-[10px] font-bold ${filter === "unread" ? "text-emerald-500" : "text-white"}`}
              >
                {notifications.filter((n) => !n.is_read).length}
              </Text>
            </View>
          )}
        </TouchableOpacity>
        <TouchableOpacity
          className={`px-4 py-2 rounded-full ${filter === "all" ? "bg-emerald-500" : "bg-gray-100"}`}
          onPress={() => setFilter("all")}
        >
          <Text
            className={`font-bold text-sm ${filter === "all" ? "text-white" : "text-gray-600"}`}
          >
            Totes
          </Text>
        </TouchableOpacity>
      </View>

      {/* Contingut o llista */}
      {loading ? (
        <View className="flex-1 justify-center items-center">
          <ActivityIndicator size="large" color="#10B981" />
        </View>
      ) : (
        <FlatList
          data={filteredNotifications}
          keyExtractor={(item, index) =>
            item.id?.toString() || index.toString()
          }
          contentContainerStyle={{ padding: 24, paddingBottom: 60 }}
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={handleRefresh}
              colors={["#10B981"]}
            />
          }
          ListEmptyComponent={
            <View className="flex-1 items-center justify-center pt-20 px-6">
              <View className="w-20 h-20 bg-gray-100 rounded-full items-center justify-center mb-4">
                <BellOff color="#9CA3AF" size={32} />
              </View>
              <Text className="text-lg font-bold text-gray-900 text-center mb-1">
                Tot al dia!
              </Text>
              <Text className="text-gray-500 text-center">
                No tens cap notificació en aquest apartat de moment.
              </Text>
            </View>
          }
          renderItem={({ item }) => (
            <TouchableOpacity
              onPress={() => handleMarkAsRead(item.id, item.is_read)}
              activeOpacity={item.is_read ? 1 : 0.7}
              className={`bg-white p-4 rounded-2xl border border-gray-100 flex-row items-start mb-3 shadow-sm ${item.is_read ? "opacity-60" : "opacity-100"}`}
            >
              {getNotificationIcon(item.tipus, item.is_read)}

              <View className="flex-1 space-y-1">
                <View className="flex-row items-center justify-between pr-2">
                  <Text
                    className={`text-base font-bold text-gray-900 flex-1 ${item.is_read ? "font-medium text-gray-500" : ""}`}
                    numberOfLines={1}
                  >
                    {item.title}
                  </Text>
                  {!item.is_read && (
                    <View className="w-2.5 h-2.5 rounded-full bg-emerald-500 ml-2" />
                  )}
                </View>

                <Text
                  className={`text-sm text-gray-600 leading-5 pr-2 ${item.is_read ? "text-gray-400" : ""}`}
                >
                  {item.message}
                </Text>

                <Text className="text-[11px] text-gray-400 font-medium pt-1">
                  {formatDate(item.created_at)}
                </Text>
              </View>
            </TouchableOpacity>
          )}
        />
      )}
    </View>
  );
}
