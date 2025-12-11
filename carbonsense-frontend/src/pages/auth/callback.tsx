import { useEffect, useState } from 'react';
import { useLocation } from 'wouter';
import { supabase } from '@/lib/supabase';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Leaf, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function AuthCallback() {
  const [, setLocation] = useLocation();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        // Get the hash parameters from the URL
        const hashParams = new URLSearchParams(window.location.hash.substring(1));
        const accessToken = hashParams.get('access_token');
        const refreshToken = hashParams.get('refresh_token');
        const type = hashParams.get('type');

        // Also check for query parameters (some Supabase flows use these)
        const queryParams = new URLSearchParams(window.location.search);
        const tokenHash = queryParams.get('token_hash');
        const queryType = queryParams.get('type');

        if (accessToken && refreshToken) {
          // Set the session using the tokens from the URL
          const { error } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          });

          if (error) {
            throw error;
          }

          setStatus('success');
          // Redirect to login with success message after a short delay
          setTimeout(() => {
            setLocation('/login?verified=true');
          }, 2000);
        } else if (tokenHash && queryType === 'signup') {
          // Handle email confirmation with token_hash
          const { error } = await supabase.auth.verifyOtp({
            token_hash: tokenHash,
            type: 'signup',
          });

          if (error) {
            throw error;
          }

          setStatus('success');
          setTimeout(() => {
            setLocation('/login?verified=true');
          }, 2000);
        } else {
          // Try to exchange the code if present
          const { error } = await supabase.auth.exchangeCodeForSession(window.location.href);

          if (error) {
            throw error;
          }

          setStatus('success');
          setTimeout(() => {
            setLocation('/login?verified=true');
          }, 2000);
        }
      } catch (error: any) {
        console.error('Auth callback error:', error);
        setStatus('error');
        setErrorMessage(error.message || 'Failed to verify email. Please try again.');
      }
    };

    handleAuthCallback();
  }, [setLocation]);

  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <div className="flex items-center justify-center mb-2">
            <Leaf className="h-10 w-10 text-primary" />
          </div>
          <CardTitle className="text-2xl text-center">
            {status === 'loading' && 'Verifying Email...'}
            {status === 'success' && 'Email Verified!'}
            {status === 'error' && 'Verification Failed'}
          </CardTitle>
          <CardDescription className="text-center">
            {status === 'loading' && 'Please wait while we verify your email address.'}
            {status === 'success' && 'Your email has been verified. Redirecting to login...'}
            {status === 'error' && errorMessage}
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-center space-y-4">
          {status === 'loading' && (
            <Loader2 className="h-12 w-12 animate-spin text-primary" />
          )}
          {status === 'success' && (
            <CheckCircle className="h-12 w-12 text-green-500" />
          )}
          {status === 'error' && (
            <>
              <XCircle className="h-12 w-12 text-destructive" />
              <Button onClick={() => setLocation('/login')} className="mt-4">
                Back to Login
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
