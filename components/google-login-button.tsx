'use client';

import { GoogleLogin } from '@react-oauth/google';
import Swal from 'sweetalert2';

export function GoogleLoginButton() {
  const handleSuccess = async (credentialResponse: any) => {
    try {
      console.log('Google 登录成功，Token:', credentialResponse.credential);

      // 发送 Token 到后端
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${API_BASE_URL}/api/auth/google-login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          google_token: credentialResponse.credential
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Google 登入失敗');
      }

      const data = await response.json();
      console.log('后端返回:', data);

      // 保存 JWT Token 到 localStorage
      localStorage.setItem('access_token', data.access_token);

      // 提示用户後直接跳轉（hard navigation 確保新頁面 fresh mount 並重讀 token）
      await Swal.fire({
        icon: 'success',
        title: '登入成功！',
        text: '',
        timer: 1000,
        showConfirmButton: false
      });

      window.location.href = '/videos';

    } catch (error) {
      console.error('Google 登录错误:', error);
      Swal.fire({
        icon: 'error',
        title: '登入失敗',
        text: (error as Error).message,
        confirmButtonText: '確定'
      });
    }
  };

  const handleError = () => {
    console.error('Google 登入失敗');
    Swal.fire({
      icon: 'error',
      title: 'Google 登入失敗',
      text: '请重试或联系支持',
      confirmButtonText: '確定'
    });
  };

  return (
    <div className="google-login-container flex justify-center">
      <GoogleLogin
        onSuccess={handleSuccess}
        onError={handleError}
        useOneTap={false}
        text="signin_with"
        shape="rectangular"
        size="large"
        theme="outline"
        logo_alignment="left"
      />
    </div>
  );
}
