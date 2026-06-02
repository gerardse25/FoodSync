import { useAuth } from "@/src/context/AuthContext";
import { router } from "expo-router";
import {
  ArrowLeft,
  ArrowUpRight,
  CalendarDays,
  CheckCircle2,
} from "lucide-react-native";
import React, { useEffect, useMemo, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  ScrollView,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import {
  expensesService,
  type ExpensesPeriod,
} from "../../services/expensesService";
import { homeService } from "../../services/homeService";

function roundToCents(value: number) {
  return Math.round(value * 100) / 100;
}

function normalizeMoneyValue(value: string | number | null | undefined) {
  const num = typeof value === "string" ? Number(value) : (value ?? 0);
  if (Number.isNaN(num)) return 0;

  const rounded = roundToCents(num);
  return Math.abs(rounded) < 0.01 ? 0 : rounded;
}

function isZeroMoney(value: string | number | null | undefined) {
  return normalizeMoneyValue(value) === 0;
}

function formatMoney(value: string | number | null | undefined) {
  const normalized = normalizeMoneyValue(value);
  return `${normalized.toFixed(2)}€`;
}

function getPeriodLabel(period: ExpensesPeriod) {
  if (period === "weekly") return "Setmanal";
  if (period === "yearly") return "Anual";
  return "Mensual";
}

function getBarHeight(value: number, max: number) {
  if (max <= 0) return 24;
  return Math.max(24, (value / max) * 120);
}

export default function ExpensesScreen() {
  const { session } = useAuth();

  const [period, setPeriod] = useState<ExpensesPeriod>("monthly");
  const [summary, setSummary] = useState<any>(null);
  const [split, setSplit] = useState<any>(null);
  const [members, setMembers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [payingTransferKey, setPayingTransferKey] = useState<string | null>(
    null,
  );

  const currentUserId = session?.id ? String(session.id) : null;

  const memberNameById = useMemo(() => {
    const map: Record<string, string> = {};

    members.forEach((member: any) => {
      const id = String(member.user_id ?? member.id ?? member.id_usuari ?? "");
      if (id) {
        map[id] = member.username ?? member.nom ?? member.name ?? "Usuari";
      }
    });

    return map;
  }, [members]);

  const computedMembers = useMemo(() => {
    const rawMembers = split?.members ?? [];

    return rawMembers.map((member: any) => {
      const userId = String(member.user_id ?? member.id ?? "");
      const paid = normalizeMoneyValue(member.paid || 0);
      const shouldPay = normalizeMoneyValue(member.should_pay || 0);

      const settledPaid = normalizeMoneyValue(member.settled_paid || 0);

      const balance = normalizeMoneyValue(member.balance || 0);
      return {
        ...member,
        user_id: userId,
        paid,
        should_pay: shouldPay,
        settled_paid: settledPaid,
        balance,
      };
    });
  }, [split]);

  const currentUserShare = useMemo(() => {
    if (!computedMembers.length || !currentUserId) return null;

    return computedMembers.find(
      (member: any) => String(member.user_id) === String(currentUserId),
    );
  }, [computedMembers, currentUserId]);

  const transfers = useMemo(() => {
    const backendTransfers = split?.transfers ?? [];
    if (!Array.isArray(backendTransfers)) return [];

    return backendTransfers
      .map((transfer: any) => ({
        ...transfer,
        amount: normalizeMoneyValue(transfer.amount),
      }))
      .filter((transfer: any) => !isZeroMoney(transfer.amount));
  }, [split]);

  const bars = useMemo(() => {
    const series = summary?.series ?? [];
    return series.map((item: any) => ({
      ...item,
      totalNumber: normalizeMoneyValue(item.total),
    }));
  }, [summary]);

  const maxBarValue = useMemo(() => {
    if (!bars.length) return 0;
    return Math.max(...bars.map((item: any) => item.totalNumber || 0));
  }, [bars]);

  useEffect(() => {
    loadData();
  }, [period]);

  const loadData = async () => {
    try {
      setLoading(true);

      const [summaryData, splitData, homeData] = await Promise.all([
        expensesService.getSummary({ period }),
        expensesService.getSplit(),
        homeService.getHome(),
      ]);

      setSummary(summaryData);
      setSplit(splitData);
      setMembers(homeData?.members || homeData?.membres || []);
    } catch (error: any) {
      Alert.alert(
        "Error",
        typeof error === "string"
          ? error
          : "No s'han pogut carregar les despeses",
      );
    } finally {
      setLoading(false);
    }
  };

  const handleMarkTransferPaid = async (transfer: any) => {
    const normalizedAmount = normalizeMoneyValue(transfer.amount);
    const transferKey = `${transfer.from_user_id}-${transfer.to_user_id}-${normalizedAmount}`;

    try {
      setPayingTransferKey(transferKey);

      const response = await expensesService.createSettlement({
        from_user_id: transfer.from_user_id,
        to_user_id: transfer.to_user_id,
        amount: normalizedAmount.toFixed(2),
        date_from: split?.date_from || null,
        date_to: split?.date_to || null,
      });

      if (response?.split) {
        setSplit(response.split);
      } else {
        await loadData();
      }

      Alert.alert(
        "Pagament registrat",
        response?.missatge || "S'ha registrat correctament.",
      );
    } catch (error: any) {
      Alert.alert(
        "Error",
        typeof error === "string"
          ? error
          : "No s'ha pogut registrar el pagament",
      );
    } finally {
      setPayingTransferKey(null);
    }
  };

  if (loading) {
    return (
      <SafeAreaView className="flex-1 bg-[#F8FAF8] justify-center items-center">
        <ActivityIndicator size="large" color="#10B981" />
        <Text className="text-gray-500 mt-4">Carregant despeses...</Text>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView className="flex-1 bg-[#F8FAF8]">
      <View className="px-4 pt-3 pb-4 bg-white border-b border-gray-200 flex-row items-center">
        <TouchableOpacity
          className="w-10 h-10 rounded-xl items-center justify-center"
          onPress={() => router.back()}
        >
          <ArrowLeft color="#1F2937" size={24} />
        </TouchableOpacity>

        <Text className="flex-1 text-center text-2xl font-bold text-gray-900 mr-10">
          Despeses
        </Text>
      </View>

      <ScrollView
        className="flex-1"
        contentContainerStyle={{ padding: 24, paddingBottom: 40 }}
        showsVerticalScrollIndicator={false}
      >
        <View className="flex-row items-center justify-between mb-5">
          <Text className="text-2xl font-bold text-gray-900">Resum</Text>

          <View className="flex-row">
            {(["weekly", "monthly", "yearly"] as ExpensesPeriod[]).map(
              (item) => (
                <TouchableOpacity
                  key={item}
                  className={`ml-2 rounded-2xl px-4 py-3 border ${
                    period === item
                      ? "bg-emerald-500 border-emerald-500"
                      : "bg-white border-gray-200"
                  }`}
                  onPress={() => setPeriod(item)}
                >
                  <View className="flex-row items-center">
                    <CalendarDays
                      color={period === item ? "#FFFFFF" : "#6B7280"}
                      size={16}
                    />
                    <Text
                      className={`ml-2 font-medium ${
                        period === item ? "text-white" : "text-gray-700"
                      }`}
                    >
                      {getPeriodLabel(item)}
                    </Text>
                  </View>
                </TouchableOpacity>
              ),
            )}
          </View>
        </View>

        <View className="bg-emerald-500 rounded-[28px] p-6 mb-6">
          <View className="flex-row justify-between items-start">
            <View className="flex-1 pr-3">
              <Text className="text-emerald-50 text-sm mb-2">
                Despesa total de la llar
              </Text>
              <Text className="text-white text-5xl font-bold">
                {formatMoney(summary?.total || 0)}
              </Text>
            </View>

            <View className="bg-emerald-400/60 rounded-full px-3 py-2 flex-row items-center">
              <ArrowUpRight color="#FFFFFF" size={16} />
              <Text className="text-white font-semibold ml-1">
                {summary?.item_count || 0} items
              </Text>
            </View>
          </View>

          <View className="h-px bg-emerald-300 my-6" />

          <View className="flex-row justify-between">
            <View>
              <Text className="text-emerald-100 text-sm">La teva part</Text>
              <Text className="text-white text-3xl font-bold mt-1">
                {currentUserShare
                  ? formatMoney(currentUserShare.should_pay)
                  : "0.00€"}
              </Text>
            </View>

            <View>
              <Text className="text-emerald-100 text-sm">Per persona</Text>
              <Text className="text-white text-3xl font-bold mt-1">
                {computedMembers.length
                  ? formatMoney(
                      normalizeMoneyValue(summary?.total || 0) /
                        computedMembers.length,
                    )
                  : "0.00€"}
              </Text>
            </View>
          </View>
        </View>

        <View className="bg-white rounded-3xl p-5 border border-gray-100 shadow-sm mb-6">
          <Text className="text-xl font-bold text-gray-900 mb-5">
            Evolució de despeses
          </Text>

          <View className="flex-row items-end justify-between h-40">
            {bars.length > 0 ? (
              bars.map((item: any, index: number) => (
                <View
                  key={`${item.period}-${index}`}
                  className="items-center flex-1"
                >
                  <View
                    className="w-12 rounded-t-2xl bg-emerald-500"
                    style={{
                      height: getBarHeight(item.totalNumber, maxBarValue),
                    }}
                  />
                  <Text className="text-xs text-gray-500 mt-2 text-center">
                    {item.period}
                  </Text>
                </View>
              ))
            ) : (
              <View className="flex-1 items-center justify-center">
                <Text className="text-gray-400">
                  No hi ha dades per mostrar
                </Text>
              </View>
            )}
          </View>
        </View>

        <View className="bg-white rounded-3xl p-5 border border-gray-100 shadow-sm mb-6">
          <Text className="text-xl font-bold text-gray-900 mb-5">
            Repartiment per membre
          </Text>

          {computedMembers.length > 0 ? (
            computedMembers.map((member: any, index: number) => {
              const memberId = String(member.user_id);
              const memberName =
                memberNameById[memberId] ||
                member.username ||
                member.nom ||
                "Usuari";

              const paid = member.paid;
              const shouldPay = member.should_pay;
              const balance = member.balance;

              return (
                <View
                  key={`${memberId}-${index}`}
                  className={`flex-row items-center justify-between ${
                    index !== computedMembers.length - 1
                      ? "mb-6 pb-6 border-b border-gray-100"
                      : ""
                  }`}
                >
                  <View className="flex-1 pr-4">
                    <Text className="text-2xl font-bold text-gray-900">
                      {memberName}
                      {memberId === currentUserId && (
                        <Text className="text-sm font-semibold text-gray-500">
                          {" "}
                          (Tú)
                        </Text>
                      )}
                    </Text>

                    <View className="flex-1 pr-4">
                      <Text className="text-gray-500 mt-2 text-base">
                        Compres: {formatMoney(paid)}
                        {member.settled_paid > 0
                          ? ` (+${formatMoney(member.settled_paid)} en deutes)`
                          : ""}
                        <Text className="text-xl text-gray-300"> | </Text>
                        <Text className="text-gray-500 mt-2 text-base">
                          Li tocava: {formatMoney(shouldPay)}
                        </Text>
                      </Text>
                    </View>
                  </View>

                  {isZeroMoney(balance) ? (
                    <View className="bg-emerald-50 rounded-full px-4 py-2">
                      <Text className="text-emerald-700 font-bold">0.00€</Text>
                    </View>
                  ) : balance > 0 ? (
                    <View className="bg-emerald-50 rounded-full px-4 py-2">
                      <Text className="text-emerald-700 font-bold">
                        Rep {formatMoney(balance)}
                      </Text>
                    </View>
                  ) : (
                    <View className="bg-red-50 rounded-full px-4 py-2">
                      <Text className="text-red-600 font-bold">
                        Paga {formatMoney(Math.abs(balance))}
                      </Text>
                    </View>
                  )}
                </View>
              );
            })
          ) : (
            <Text className="text-gray-400">
              No hi ha dades de repartiment.
            </Text>
          )}
        </View>

        <View className="bg-white rounded-3xl p-5 border border-gray-100 shadow-sm">
          <Text className="text-xl font-bold text-gray-900 mb-5">
            Transferències recomanades
          </Text>

          {transfers.length > 0 ? (
            transfers.map((transfer: any, index: number) => {
              const normalizedAmount = normalizeMoneyValue(transfer.amount);
              const transferKey = `${transfer.from_user_id}-${transfer.to_user_id}-${normalizedAmount}`;

              const fromName =
                String(transfer.from_user_id) === String(currentUserId)
                  ? "Tu"
                  : memberNameById[String(transfer.from_user_id)] || "Usuari";

              const toName =
                String(transfer.to_user_id) === String(currentUserId)
                  ? " (Tú)"
                  : memberNameById[String(transfer.to_user_id)] || "Usuari";

              return (
                <View
                  key={`${transferKey}-${index}`}
                  className={`${
                    index !== transfers.length - 1
                      ? "mb-4 pb-4 border-b border-gray-100"
                      : ""
                  }`}
                >
                  <View className="flex-row items-center justify-between">
                    <View className="flex-1 pr-4">
                      <Text className="text-base font-semibold text-gray-900">
                        {fromName} paga a{" "}
                        {memberNameById[String(transfer.to_user_id)] ||
                          "Usuari"}
                        <Text className="text-sm font-medium text-gray-500">
                          {toName}
                        </Text>
                      </Text>
                      <Text className="text-gray-500 mt-1">
                        Import: {formatMoney(normalizedAmount)}
                      </Text>
                    </View>

                    <TouchableOpacity
                      className={`rounded-2xl px-4 py-3 flex-row items-center ${
                        payingTransferKey === transferKey
                          ? "bg-emerald-300"
                          : "bg-emerald-500"
                      }`}
                      onPress={() =>
                        handleMarkTransferPaid({
                          ...transfer,
                          amount: String(normalizedAmount),
                        })
                      }
                      disabled={payingTransferKey === transferKey}
                    >
                      {payingTransferKey === transferKey ? (
                        <ActivityIndicator color="#FFFFFF" size="small" />
                      ) : (
                        <>
                          <CheckCircle2 color="#FFFFFF" size={16} />
                          <Text className="text-white font-semibold ml-2">
                            Pagar
                          </Text>
                        </>
                      )}
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })
          ) : (
            <Text className="text-gray-400">
              No hi ha transferències pendents.
            </Text>
          )}
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}
