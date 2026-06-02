import { router, useFocusEffect } from "expo-router";
import {
  CalendarDays,
  ChevronDown,
  ChevronRight,
  Lock,
  Package,
  Search,
  SlidersHorizontal,
  Users,
  X,
} from "lucide-react-native";
import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ActivityIndicator,
  FlatList,
  Image,
  Modal,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { authService } from "../../services/authService";
import { homeService, type HomeMember } from "../../services/homeService";
import {
  inventoryService,
  type InventoryCategoryOption,
  type InventoryProduct,
} from "../../services/inventoryService";

const NUTRITION_OPTIONS = ["A", "B", "C", "D", "E"];
const EXPIRY_OPTIONS = [
  { label: "Proxims", value: "expiring_soon" },
  { label: "Caducats", value: "expired" },
  { label: "Frescs", value: "ok" },
];

export default function InventoryScreen() {
  const [products, setProducts] = useState<InventoryProduct[]>([]);
  const [categories, setCategories] = useState<InventoryCategoryOption[]>([]);
  const [members, setMembers] = useState<HomeMember[]>([]);

  const [search, setSearch] = useState("");
  const [categoria, setCategoria] = useState("");
  const [ownerUserId, setOwnerUserId] = useState("");
  const [minQuantity, setMinQuantity] = useState("");
  const [maxQuantity, setMaxQuantity] = useState("");
  const [nutritionScore, setNutritionScore] = useState("");
  const [expiryFilter, setExpiryFilter] = useState("");

  const [showFilters, setShowFilters] = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);
  const [showOwnerModal, setShowOwnerModal] = useState(false);

  const [loading, setLoading] = useState(true);
  const [loadingCategories, setLoadingCategories] = useState(false);
  const [loadingMembers, setLoadingMembers] = useState(false);
  const [error, setError] = useState("");

  const [currentUserId, setCurrentUserId] = useState<string | null>(null);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fetchCurrentUser = async () => {
    try {
      const result = await authService.verify();
      const userId =
        result?.user?.id ||
        result?.user?.id_usuari ||
        result?.user?.user_id ||
        result?.id ||
        null;

      setCurrentUserId(userId ? String(userId) : null);
    } catch {
      setCurrentUserId(null);
    }
  };

  const fetchInventory = async (
    overrideSearch?: string,
    showLoader: boolean = true,
  ) => {
    try {
      if (showLoader) setLoading(true);
      setError("");

      const data = await inventoryService.getInventoryProducts({
        search: overrideSearch ?? search,
        categoria,
        owner_user_id: ownerUserId || undefined,
        min_quantity: minQuantity ? Number(minQuantity) : undefined,
        max_quantity: maxQuantity ? Number(maxQuantity) : undefined,
        nutrition_score: nutritionScore || undefined,
        expiry_filter: expiryFilter || undefined,
      });

      setProducts(data);
    } catch (err: any) {
      setError(
        typeof err === "string" ? err : "No s'ha pogut carregar l'inventari",
      );
    } finally {
      if (showLoader) setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      setLoadingCategories(true);
      const data = await inventoryService.getCategories();
      setCategories(data);
    } finally {
      setLoadingCategories(false);
    }
  };

  const extractMembers = (data: any): HomeMember[] => {
    const candidates = [
      data?.membres,
      data?.members,
      data?.home?.membres,
      data?.home?.members,
      data?.llar?.membres,
      data?.llar?.members,
      data?.data?.membres,
      data?.data?.members,
      data?.data?.home?.membres,
      data?.data?.home?.members,
      data?.data?.llar?.membres,
      data?.data?.llar?.members,
    ];

    const rawMembers = candidates.find((item) => Array.isArray(item)) || [];

    return rawMembers
      .map((member: any) => ({
        id_usuari: String(
          member?.id_usuari ?? member?.id ?? member?.user_id ?? "",
        ),
        nom: String(
          member?.nom ?? member?.name ?? member?.username ?? "Usuari",
        ),
      }))
      .filter((member: HomeMember) => member.id_usuari);
  };

  const fetchMembers = async () => {
    try {
      setLoadingMembers(true);
      const homeData = await homeService.getHome();
      const parsedMembers = extractMembers(homeData);
      setMembers(parsedMembers);
    } catch {
      setMembers([]);
    } finally {
      setLoadingMembers(false);
    }
  };

  useFocusEffect(
    useCallback(() => {
      fetchCurrentUser();
      fetchCategories();
      fetchMembers();
      fetchInventory(undefined, false);
    }, [
      search,
      categoria,
      ownerUserId,
      minQuantity,
      maxQuantity,
      nutritionScore,
      expiryFilter,
    ]),
  );

  useEffect(() => {
    fetchInventory();
  }, []);

  useEffect(() => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      fetchInventory(search, false);
    }, 350);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [search]);

  const applyFilters = () => {
    setShowFilters(false);
    fetchInventory(undefined, false);
  };

  const clearFilters = async () => {
    setSearch("");
    setCategoria("");
    setOwnerUserId("");
    setMinQuantity("");
    setMaxQuantity("");
    setNutritionScore("");
    setExpiryFilter("");
    setShowFilters(false);

    try {
      setError("");
      const data = await inventoryService.getInventoryProducts();
      setProducts(data);
    } catch (err: any) {
      setError(
        typeof err === "string" ? err : "No s'ha pogut carregar l'inventari",
      );
    } finally {
      setLoading(false);
    }
  };

  const activeFiltersCount =
    (categoria ? 1 : 0) +
    (ownerUserId ? 1 : 0) +
    (minQuantity ? 1 : 0) +
    (maxQuantity ? 1 : 0) +
    (nutritionScore ? 1 : 0) +
    (expiryFilter ? 1 : 0);

  const selectedCategoryLabel = categoria || "Totes les categories";

  const selectedOwnerLabel =
    members.find((member) => String(member.id_usuari) === String(ownerUserId))
      ?.nom || "Tots els usuaris";

  const uniqueCategories = useMemo(() => {
    const seen = new Set<string>();
    return categories.filter((cat) => {
      const key = `${cat.value}|${cat.label}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [categories]);

  const uniqueMembers = useMemo(() => {
    const seen = new Set<string>();
    return members.filter((member) => {
      const key = `${member.id_usuari}|${member.nom}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [members]);

  const isProductAccessible = (product: InventoryProduct) => {
    if (!product.es_privat) return true;
    if (!currentUserId) return false;

    return product.propietaris.some(
      (owner) => String(owner.id_usuari) === String(currentUserId),
    );
  };

  const handleProductPress = (product: InventoryProduct) => {
    router.push({
      pathname: "/product/[id]",
      params: {
        id: product.id_producte,
        isOwner: isProductAccessible(product) ? "1" : "0",
      },
    });
  };

  const renderPrivateInfo = (product: InventoryProduct) => {
    if (!product.es_privat) {
      return {
        icon: <Users size={12} color="#059669" />,
        text: "Compartit",
        className:
          "self-start flex-row items-center rounded-full border border-emerald-200 bg-emerald-50 px-2.5 py-0.5",
        textClassName: "ml-1 text-[12px] font-semibold text-emerald-700",
      };
    }

    const owners =
      product.propietaris.length > 0
        ? product.propietaris.map((owner) => owner.nom).join(", ")
        : "Sense propietari";

    return {
      icon: <Lock size={12} color="#D97706" />,
      text: `Privat · ${owners}`,
      className:
        "self-start flex-row items-center rounded-full border border-amber-200 bg-amber-50 px-2.5 py-0.5",
      textClassName: "ml-1 text-[12px] font-semibold text-amber-700",
    };
  };

  const getNutriscoreStyle = (score?: string | null) => {
    if (!score) return null;
    const map: Record<string, { bg: string; text: string }> = {
      A: { bg: "#1E8E3E", text: "#FFFFFF" },
      B: { bg: "#85BB2F", text: "#FFFFFF" },
      C: { bg: "#FECB02", text: "#333333" },
      D: { bg: "#EE8100", text: "#FFFFFF" },
      E: { bg: "#E63312", text: "#FFFFFF" },
    };
    return map[score.toUpperCase()] ?? null;
  };

  const renderItem = ({ item }: { item: InventoryProduct }) => {
    const privacy = renderPrivateInfo(item);

    return (
      <TouchableOpacity
        className="bg-white rounded-[18px] p-3 mb-3"
        onPress={() => handleProductPress(item)}
        activeOpacity={0.85}
        style={{
          shadowColor: "#000",
          shadowOpacity: 0.02,
          shadowRadius: 6,
          shadowOffset: { width: 0, height: 2 },
          elevation: 1,
        }}
      >
        <View className="flex-row items-start">
          <View className="w-12 h-12 rounded-[16px] bg-emerald-50 items-center justify-center mr-3 overflow-hidden">
            {item.imatge_url ? (
              <Image
                source={{ uri: item.imatge_url }}
                style={{ width: 48, height: 48 }}
                resizeMode="cover"
              />
            ) : (
              <Package color="#10B981" size={20} />
            )}
          </View>

          <View className="flex-1">
            <View className="flex-row items-start justify-between">
              <Text className="text-[16px] font-bold text-slate-900 flex-1 pr-2">
                {item.nom}
              </Text>
              <ChevronRight color="#9CA3AF" size={18} />
            </View>

            <View className="flex-row flex-wrap mt-1.5">
              {item.categoria ? (
                <View className="bg-slate-100 rounded-full px-2 py-0.5 mr-2 mb-1.5">
                  <Text className="text-[12px] text-slate-700 font-medium">
                    {item.categoria}
                  </Text>
                </View>
              ) : null}

              <View className="bg-slate-100 rounded-full px-2 py-0.5 mr-2 mb-1.5">
                <Text className="text-[12px] text-slate-700 font-medium">
                  Quantitat: {item.quantitat}
                </Text>
              </View>

              {(() => {
                const nsStyle = getNutriscoreStyle(item.nutriscore);
                return nsStyle ? (
                  <View
                    className="rounded-full px-2 py-0.5 mr-2 mb-1.5"
                    style={{ backgroundColor: nsStyle.bg }}
                  >
                    <Text
                      className="text-[12px] font-bold"
                      style={{ color: nsStyle.text }}
                    >
                      {item.nutriscore!.toUpperCase()}
                    </Text>
                  </View>
                ) : null;
              })()}
            </View>

            {item.data_caducitat ? (
              <View className="flex-row items-center mt-0.5 mb-2">
                <CalendarDays size={14} color="#6B7280" />
                <Text className="ml-1.5 text-[13px] text-slate-500">
                  Caduca el {item.data_caducitat}
                </Text>
              </View>
            ) : null}

            <View className={privacy.className}>
              {privacy.icon}
              <Text className={privacy.textClassName}>{privacy.text}</Text>
            </View>
          </View>
        </View>
      </TouchableOpacity>
    );
  };

  const Chip = ({
    label,
    selected,
    onPress,
  }: {
    label: string;
    selected: boolean;
    onPress: () => void;
  }) => (
    <TouchableOpacity
      onPress={onPress}
      className={`px-4 py-2 rounded-full mr-2 mb-2 border ${
        selected
          ? "bg-emerald-500 border-emerald-500"
          : "bg-white border-gray-300"
      }`}
    >
      <Text className={selected ? "text-white font-medium" : "text-gray-700"}>
        {label}
      </Text>
    </TouchableOpacity>
  );

  return (
    <SafeAreaView className="flex-1 bg-[#F8FAF8]">
      <View className="px-6 pt-6 pb-4 bg-white border-b border-gray-200">
        <Text className="text-2xl font-bold text-gray-900">Inventari</Text>
        <Text className="text-sm text-gray-500 mt-1">
          Consulta tots els produtes de la teva llar
        </Text>
      </View>

      <ScrollView className="flex-1" showsVerticalScrollIndicator={false}>
        <View className="px-6 pt-4">
          <View className="bg-white border border-gray-200 rounded-2xl px-4 h-12 flex-row items-center">
            <Search color="#9CA3AF" size={18} />
            <TextInput
              value={search}
              onChangeText={setSearch}
              placeholder="Buscar producte..."
              placeholderTextColor="#9CA3AF"
              className="flex-1 ml-3 text-base text-gray-900"
            />
            {search ? (
              <TouchableOpacity onPress={() => setSearch("")}>
                <X color="#9CA3AF" size={18} />
              </TouchableOpacity>
            ) : null}
          </View>

          <TouchableOpacity
            className="mt-3 flex-row items-center justify-center bg-white border border-gray-200 rounded-2xl h-11"
            onPress={() => setShowFilters(!showFilters)}
          >
            <SlidersHorizontal color="#4B5563" size={18} />
            <Text className="ml-2 text-gray-700 font-medium">
              {showFilters ? "Ocultar filtres" : "Mostrar filtres"}
              {activeFiltersCount > 0 ? ` (${activeFiltersCount})` : ""}
            </Text>
          </TouchableOpacity>

          {showFilters ? (
            <View className="mt-3 bg-white border border-gray-200 rounded-2xl p-4">
              <Text className="text-sm font-medium text-gray-900 mb-2">
                Categoria
              </Text>

              {loadingCategories ? (
                <ActivityIndicator size="small" color="#10B981" />
              ) : (
                <TouchableOpacity
                  className="h-12 px-4 rounded-xl bg-gray-100 flex-row items-center justify-between mb-3"
                  onPress={() => setShowCategoryModal(true)}
                >
                  <Text
                    className={
                      categoria
                        ? "text-gray-900 text-base"
                        : "text-gray-400 text-base"
                    }
                  >
                    {selectedCategoryLabel}
                  </Text>
                  <ChevronDown color="#6B7280" size={20} />
                </TouchableOpacity>
              )}

              <Text className="text-sm font-medium text-gray-900 mb-2">
                Usuari propietari
              </Text>

              {loadingMembers ? (
                <ActivityIndicator size="small" color="#10B981" />
              ) : (
                <TouchableOpacity
                  className="h-12 px-4 rounded-xl bg-gray-100 flex-row items-center justify-between mb-3"
                  onPress={() => setShowOwnerModal(true)}
                >
                  <Text
                    className={
                      ownerUserId
                        ? "text-gray-900 text-base"
                        : "text-gray-400 text-base"
                    }
                  >
                    {selectedOwnerLabel}
                  </Text>
                  <ChevronDown color="#6B7280" size={20} />
                </TouchableOpacity>
              )}

              <Text className="text-sm font-medium text-gray-900 mb-2">
                Stock
              </Text>

              <View className="flex-row mb-3">
                <TextInput
                  value={minQuantity}
                  onChangeText={setMinQuantity}
                  placeholder="Mín."
                  placeholderTextColor="#9CA3AF"
                  keyboardType="numeric"
                  className="flex-1 h-12 px-4 rounded-xl bg-gray-100 text-base text-gray-900 mr-2"
                />
                <TextInput
                  value={maxQuantity}
                  onChangeText={setMaxQuantity}
                  placeholder="Máx."
                  placeholderTextColor="#9CA3AF"
                  keyboardType="numeric"
                  className="flex-1 h-12 px-4 rounded-xl bg-gray-100 text-base text-gray-900 ml-2"
                />
              </View>

              <Text className="text-sm font-medium text-gray-900 mb-2">
                Scoring nutricional
              </Text>

              <View className="flex-row flex-wrap mb-3">
                {NUTRITION_OPTIONS.map((score) => (
                  <Chip
                    key={score}
                    label={score}
                    selected={nutritionScore === score}
                    onPress={() =>
                      setNutritionScore((prev) => (prev === score ? "" : score))
                    }
                  />
                ))}
              </View>

              <Text className="text-sm font-medium text-gray-900 mb-2">
                Proximitat de caducitat
              </Text>

              <View className="flex-row flex-wrap">
                {EXPIRY_OPTIONS.map((option) => (
                  <Chip
                    key={option.value}
                    label={option.label}
                    selected={expiryFilter === option.value}
                    onPress={() =>
                      setExpiryFilter((prev) =>
                        prev === option.value ? "" : option.value,
                      )
                    }
                  />
                ))}
              </View>

              <View className="flex-row mt-4">
                <TouchableOpacity
                  className="flex-1 h-11 bg-emerald-500 rounded-xl items-center justify-center mr-2"
                  onPress={applyFilters}
                >
                  <Text className="text-white font-semibold">Aplicar</Text>
                </TouchableOpacity>

                <TouchableOpacity
                  className="flex-1 h-11 bg-gray-200 rounded-xl items-center justify-center ml-2"
                  onPress={clearFilters}
                >
                  <Text className="text-gray-700 font-semibold">Netejar</Text>
                </TouchableOpacity>
              </View>
            </View>
          ) : null}
        </View>

        <View className="px-6 pt-4">
          {loading ? (
            <View className="items-center justify-center py-16">
              <ActivityIndicator size="large" color="#10B981" />
              <Text className="text-gray-500 mt-4">Carregant inventari...</Text>
            </View>
          ) : error ? (
            <View className="items-center justify-center px-6 py-16">
              <Text className="text-red-500 text-center font-medium">
                {error}
              </Text>
              <TouchableOpacity
                className="mt-4 bg-emerald-500 px-5 py-3 rounded-xl"
                onPress={() => fetchInventory()}
              >
                <Text className="text-white font-semibold">Reintentar</Text>
              </TouchableOpacity>
            </View>
          ) : products.length === 0 ? (
            <View className="items-center justify-center px-6 py-16">
              <View className="w-20 h-20 rounded-full bg-emerald-50 items-center justify-center mb-4">
                <Package color="#10B981" size={30} />
              </View>
              <Text className="text-lg font-bold text-gray-900 mb-2">
                No hi ha productes
              </Text>
              <Text className="text-gray-500 text-center">
                No s&apos;han trobat productes amb aquests filtres.
              </Text>
            </View>
          ) : (
            <FlatList
              data={products}
              keyExtractor={(item) => item.id_producte}
              renderItem={renderItem}
              scrollEnabled={false}
            />
          )}
        </View>
      </ScrollView>

      <Modal
        visible={showCategoryModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowCategoryModal(false)}
      >
        <Pressable
          className="flex-1 bg-black/30 justify-center px-6"
          onPress={() => setShowCategoryModal(false)}
        >
          <Pressable className="bg-white rounded-2xl p-4 max-h-[70%]">
            <Text className="text-lg font-bold text-gray-900 mb-4">
              Selecciona una categoria
            </Text>

            <ScrollView showsVerticalScrollIndicator={false}>
              <TouchableOpacity
                className="py-3 border-b border-gray-100"
                onPress={() => {
                  setCategoria("");
                  setShowCategoryModal(false);
                }}
              >
                <Text className="text-base text-gray-900">
                  Totes les categories
                </Text>
              </TouchableOpacity>

              {uniqueCategories.map((cat, index) => (
                <TouchableOpacity
                  key={`${cat.value}-${index}`}
                  className="py-3 border-b border-gray-100"
                  onPress={() => {
                    setCategoria(cat.label);
                    setShowCategoryModal(false);
                  }}
                >
                  <Text
                    className={`text-base ${
                      categoria === cat.label
                        ? "text-emerald-600 font-semibold"
                        : "text-gray-900"
                    }`}
                  >
                    {cat.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </Pressable>
        </Pressable>
      </Modal>

      <Modal
        visible={showOwnerModal}
        transparent
        animationType="fade"
        onRequestClose={() => setShowOwnerModal(false)}
      >
        <Pressable
          className="flex-1 bg-black/30 justify-center px-6"
          onPress={() => setShowOwnerModal(false)}
        >
          <Pressable className="bg-white rounded-2xl p-4 max-h-[70%]">
            <Text className="text-lg font-bold text-gray-900 mb-4">
              Selecciona un usuari
            </Text>

            <ScrollView showsVerticalScrollIndicator={false}>
              <TouchableOpacity
                className="py-3 border-b border-gray-100"
                onPress={() => {
                  setOwnerUserId("");
                  setShowOwnerModal(false);
                }}
              >
                <Text className="text-base text-gray-900">
                  Tots els usuaris
                </Text>
              </TouchableOpacity>

              {uniqueMembers.map((member, index) => (
                <TouchableOpacity
                  key={`${member.id_usuari}-${index}`}
                  className="py-3 border-b border-gray-100"
                  onPress={() => {
                    setOwnerUserId(member.id_usuari);
                    setShowOwnerModal(false);
                  }}
                >
                  <Text
                    className={`text-base ${
                      ownerUserId === member.id_usuari
                        ? "text-emerald-600 font-semibold"
                        : "text-gray-900"
                    }`}
                  >
                    {member.nom}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
          </Pressable>
        </Pressable>
      </Modal>
    </SafeAreaView>
  );
}
