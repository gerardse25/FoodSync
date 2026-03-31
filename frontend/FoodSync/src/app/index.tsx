import React from 'react';
import { View, Text, TouchableOpacity} from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { useRouter } from 'expo-router';
import { Leaf, Refrigerator, TrendingDown } from 'lucide-react-native';
import { FeatureItem } from '../components/FeatureItem'; 
import { SafeAreaView } from 'react-native-safe-area-context';


export default function OnboardingScreen() {
  const router = useRouter();

  return (
    <SafeAreaView className="flex-1 bg-white">
      {/*StatusBar with dark style to contrast with the light background*/}
      <StatusBar style="dark" hidden={false} />
      <View className="flex-1 flex-col items-center justify-center px-6 pt-12 pb-6">
        
        {/* Logo */}
        <View className="w-20 h-20 bg-emerald-500 rounded-3xl flex items-center justify-center mb-6 shadow-lg shadow-emerald-500/30">
          <Refrigerator color="white" size={40} />
        </View>

        {/* App Name */}
        <Text className="text-4xl font-bold text-center mb-3 text-gray-900">
          FoodSync
        </Text>
        <Text className="text-xl text-gray-500 text-center mb-10">
          Gestión inteligente de neveras y compras
        </Text>

        {/* FeatureItem is a component for displaying features */}
        <View className="w-full max-w-sm mb-8 gap-y-6">
          <FeatureItem 
            icon={<TrendingDown color="#10B981" size={30} />}
            title="Reduce el desperdicio alimentario"
            description="Controla las fechas de caducidad y recibe alertas antes de que los alimentos se echen a perder"
          />
          <FeatureItem 
            icon={<Refrigerator color="#10B981" size={30} />}
            title="Inventario Inteligente"
            description="Escanea recibos para añadir automáticamente los alimentos en tu nevera"
          />
          <FeatureItem 
            icon={<Leaf color="#10B981" size={30} />}
            title="Hogares compartidos"
            description="Gestionad juntos vuestras compras y dividid vuestros gastos "
          />
        </View>
      </View>

      {/* CTA Buttons for Sign Up and Log In */}
      <View className="px-6 pb-8 gap-y-3 items-center justify-center">
        <TouchableOpacity 
          className="w-96 h-12 rounded-full bg-emerald-500 flex items-center justify-center active:bg-emerald-600"
          onPress={() => router.push('/(auth)/register')}
        >
          <Text className="text-white text-lg font-semibold">Crear cuenta</Text>
        </TouchableOpacity>
        
        <TouchableOpacity 
          className="w-96 h-12 rounded-full border-2 border-gray-200 flex items-center justify-center active:bg-gray-50"
          onPress={() => router.push('/(auth)/login')}
        >
          <Text className="text-gray-900 text-lg font-semibold">Iniciar sesión</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}