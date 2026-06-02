import * as ImagePicker from "expo-image-picker";
import { router } from "expo-router";
import { ArrowLeft, Camera, FileImage, ReceiptText } from "lucide-react-native";
import React, { useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Text,
  TouchableOpacity,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { inventoryService } from "../../../services/inventoryService";

export default function ScanReceiptScreen() {
  const [isProcessing, setIsProcessing] = useState(false);

  const handleImagePicked = async (result: ImagePicker.ImagePickerResult) => {
    if (result.canceled || !result.assets[0].uri) return;

    setIsProcessing(true);
    try {
      const response = await inventoryService.processReceiptOCR(
        result.assets[0].uri,
      );

      const products = Array.isArray(response)
        ? response
        : response.productes || [];

      if (products.length === 0) {
        Alert.alert(
          "Cap producte trobat",
          "No hem pogut identificar productes clars al tiquet.",
        );
        return;
      }

      const routeObj: any = {
        pathname: "/(tabs)/products/receiptSummary",
        params: { productsData: JSON.stringify(products) },
      };

      router.push(routeObj);
    } catch (error: any) {
      Alert.alert("Error de lectura", error);
    } finally {
      setIsProcessing(false);
    }
  };

  const openCamera = async () => {
    const permission = await ImagePicker.requestCameraPermissionsAsync();
    if (!permission.granted) {
      Alert.alert(
        "Permís denegat",
        "Necessitem accés a la càmera per fer fotos al tiquet.",
      );
      return;
    }

    const result = await ImagePicker.launchCameraAsync({
      mediaTypes: ["images"], 
      allowsEditing: true,
      quality: 0.8,
    });

    handleImagePicked(result);
  };

  const openGallery = async () => {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert("Permís denegat", "Necessitem accés a la galeria.");
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ["images"], 
      allowsEditing: true,
      quality: 0.8,
    });

    handleImagePicked(result);
  };

  return (
    <SafeAreaView edges={["top"]} className="flex-1 bg-[#F8FAF8]">
      <View className="px-4 py-4 flex-row items-center border-b border-gray-100 bg-white">
        <TouchableOpacity
          onPress={() => router.back()}
          className="p-2 -ml-2"
          disabled={isProcessing}
        >
          <ArrowLeft color="#1F2937" size={24} />
        </TouchableOpacity>
        <Text className="text-xl font-bold text-gray-900 ml-2">
          Escanear Tiquet
        </Text>
      </View>

      <View className="flex-1 items-center justify-center px-6">
        <View className="w-24 h-24 bg-emerald-50 rounded-full items-center justify-center mb-6">
          <ReceiptText color="#10B981" size={40} />
        </View>
        <Text className="text-2xl font-bold text-gray-900 mb-2 text-center">
          Afegeix la teva compra
        </Text>
        <Text className="text-gray-500 text-center mb-10 px-4">
          Fes una foto al teu tiquet de compra o puja&apos;l des de la teva
          galeria per afegir els productes automàticament.
        </Text>

        <View className="w-full space-y-4">
          <TouchableOpacity
            className="w-full h-16 bg-emerald-500 rounded-2xl flex-row items-center justify-center shadow-sm active:bg-emerald-600"
            onPress={openCamera}
            disabled={isProcessing}
          >
            <Camera color="white" size={24} />
            <Text className="text-white font-bold text-lg ml-3">
              Fer una foto
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            className="w-full h-16 bg-white border border-gray-200 rounded-2xl flex-row items-center justify-center active:bg-gray-50 mt-6"
            onPress={openGallery}
            disabled={isProcessing}
          >
            <FileImage color="#4B5563" size={24} />
            <Text className="text-gray-700 font-bold text-lg ml-3">
              Pujar des de la galeria
            </Text>
          </TouchableOpacity>
        </View>

        <TouchableOpacity
          className="mt-8"
          onPress={() => {
            router.replace(
              "/(tabs)/products/addManualProducts" as unknown as any,
            );
          }}
          disabled={isProcessing}
        >
          <Text className="text-emerald-500 font-bold text-base">
            Afegir manualment
          </Text>
        </TouchableOpacity>
      </View>

      {/* Modal de Carga */}
      {isProcessing && (
        <View className="absolute inset-0 bg-black/60 items-center justify-center z-50">
          <View className="bg-white p-6 rounded-3xl items-center shadow-xl w-72">
            <ActivityIndicator size="large" color="#10B981" />
            <Text className="text-gray-900 font-bold mt-4 text-lg text-center">
              Llegint el tiquet...
            </Text>
            <Text className="text-gray-500 text-sm mt-1 text-center">
              Això pot trigar uns segons per la IA
            </Text>
          </View>
        </View>
      )}
    </SafeAreaView>
  );
}
