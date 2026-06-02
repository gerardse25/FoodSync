import { CameraView, useCameraPermissions } from "expo-camera";
import { router } from "expo-router";
import { Edit3, ScanBarcode, X } from "lucide-react-native";
import React, { useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import {
  SafeAreaView,
  useSafeAreaInsets,
} from "react-native-safe-area-context";

import { inventoryService } from "../../../services/inventoryService";

export default function ScanBarcodeScreen() {
  const [permission, requestPermission] = useCameraPermissions();

  const [isScanning, setIsScanning] = useState(false);
  const isScanningRef = useRef(false);

  const insets = useSafeAreaInsets();

  const HOLE_SIZE = 280;
  const MASK_SIZE = 2000;
  const BORDER_WIDTH = (MASK_SIZE - HOLE_SIZE) / 2;
  const INNER_RADIUS = 28;
  const OUTER_RADIUS = INNER_RADIUS + BORDER_WIDTH;

  if (!permission) return <View className="flex-1 bg-black" />;

  if (!permission.granted) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center bg-[#F8FAF8] px-6">
        <View className="w-20 h-20 rounded-full bg-emerald-50 items-center justify-center mb-6">
          <ScanBarcode color="#10B981" size={32} />
        </View>
        <Text className="text-center text-xl font-bold text-gray-900 mb-2">
          Accés a la càmera
        </Text>
        <Text className="text-center text-base text-gray-500 mb-8">
          Necessitem el teu permís per utilitzar la càmera i escanejar
          productes.
        </Text>
        <TouchableOpacity
          className="w-full h-14 bg-emerald-500 rounded-2xl items-center justify-center shadow-sm"
          onPress={requestPermission}
        >
          <Text className="text-white font-bold text-lg">Donar permís</Text>
        </TouchableOpacity>
        <TouchableOpacity className="mt-4 p-4" onPress={() => router.back()}>
          <Text className="text-gray-500 font-medium text-base">
            Tornar enrere
          </Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  const handleBarcodeScanned = async ({
    data,
  }: {
    type: string;
    data: string;
  }) => {
    if (isScanning) return;
    setIsScanning(true);

    try {
      const result = await inventoryService.lookupBarcode(data);

      router.push({
        pathname: "/products/barcodeSummary",
        params: {
          barcode: data,
          found: result.found ? "true" : "false",
        },
      });
    } catch (error: any) {
      Alert.alert("Error de lectura", error);
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <View className="flex-1 bg-black relative">
      <CameraView
        style={StyleSheet.absoluteFillObject}
        facing="back"
        onBarcodeScanned={isScanning ? undefined : handleBarcodeScanned}
        barcodeScannerSettings={{
          barcodeTypes: ["ean13", "ean8", "upc_a", "upc_e"],
        }}
      />
      <View
        style={StyleSheet.absoluteFill}
        className="items-center justify-center pointer-events-none"
      >
        <View
          style={{
            position: "absolute",
            width: MASK_SIZE,
            height: MASK_SIZE,
            borderWidth: BORDER_WIDTH,
            borderRadius: OUTER_RADIUS,
            borderColor: "rgba(0,0,0,0.6)",
          }}
        />

        <View
          style={{
            width: HOLE_SIZE,
            height: HOLE_SIZE,
            borderWidth: 3,
            borderColor: "white",
            borderRadius: INNER_RADIUS,
            justifyContent: "center",
            alignItems: "center",
            overflow: "hidden",
          }}
        >
          {!isScanning && (
            <View className="w-full h-0.5 bg-emerald-500 shadow-[0_0_10px_#10B981]" />
          )}
        </View>

        <View
          className="absolute"
          style={{ top: "50%", marginTop: HOLE_SIZE / 2 + 30 }}
        >
          <Text className="text-white text-[15px] font-medium text-center px-8 shadow-sm">
            Col·loca el codi de barres a l&apos;interior del requadre.
          </Text>
        </View>
      </View>

      <SafeAreaView className="absolute top-0 w-full z-10 pointer-events-box-none">
        <View className="flex-row items-center px-6 pt-2">
          <TouchableOpacity
            className="w-11 h-11 bg-white rounded-full items-center justify-center z-20 shadow-sm"
            onPress={() => router.back()}
            disabled={isScanning}
          >
            <X color="#1F2937" size={24} strokeWidth={2.5} />
          </TouchableOpacity>

          <View className="absolute left-0 right-0 items-center pointer-events-none mt-2">
            <Text className="text-white font-bold text-[17px] tracking-wide shadow-sm">
              Escanear Codi de barres
            </Text>
          </View>
        </View>
      </SafeAreaView>

      <View
        className="absolute bottom-0 w-full bg-white rounded-t-[32px] px-6 pt-8 z-10 shadow-xl"
        style={{ paddingBottom: Math.max(insets.bottom + 20, 40) }}
      >
        <TouchableOpacity
          className="w-full h-[56px] bg-emerald-500 rounded-2xl flex-row items-center justify-center space-x-3 active:bg-emerald-600"
          onPress={() => router.replace("/(tabs)/products/addManualProducts")}
          disabled={isScanning}
        >
          <Edit3 color="#FFFFFF" size={22} strokeWidth={2.5} />
          <Text className="text-white font-bold text-[17px] ml-2">
            Introduir producte manualment
          </Text>
        </TouchableOpacity>
      </View>

      {isScanning && (
        <View className="absolute inset-0 bg-black/70 items-center justify-center z-50">
          <View className="bg-white p-6 rounded-3xl items-center shadow-xl w-64">
            <ActivityIndicator size="large" color="#10B981" />
            <Text className="text-gray-900 font-bold mt-4 text-lg">
              Cercant...
            </Text>
            <Text className="text-gray-500 text-sm mt-1 text-center">
              Consultant la base de dades
            </Text>
          </View>
        </View>
      )}
    </View>
  );
}
