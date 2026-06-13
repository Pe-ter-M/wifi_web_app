import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { packagesApi, subscriptionsApi, paymentsApi, settingsApi } from '../services/api';
import Layout from '../components/Layout';
import PackageCard from '../components/PackageCard';
import type { Plan, MyCredential, CompanyInfo } from '../types';

export default function PaymentPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [myCreds, setMyCreds] = useState<MyCredential[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<Plan | null>(null);
  const [company, setCompany] = useState<CompanyInfo | null>(null);
  const [paying, setPaying] = useState(false);
  const [success, setSuccess] = useState(false);
  const [result, setResult] = useState<any>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const [pkgList, comp, creds] = await Promise.all([
          packagesApi.list(),
          settingsApi.get(),
          subscriptionsApi.myCredentials(),
        ]);
        setPlans(pkgList.filter((p: Plan) => p.is_active));
        setCompany(comp.company);
        setMyCreds(creds);
      } catch (err) {
        console.error(err);
      }
    };
    load();
  }, []);

  const handlePay = async () => {
    if (!selectedPlan || !user) return;
    setPaying(true);
    try {
      // Use the first subscription belonging to this customer
      const mySub = myCreds.length > 0 ? myCreds[0] : null;
      if (!mySub) {
        alert('No subscription found. Please contact admin to create one first.');
        setPaying(false);
        return;
      }
      const resp = await paymentsApi.simulate({
        subscription_id: mySub.id,
        plan_id: selectedPlan.id,
      });
      setResult(resp);
      setSuccess(true);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Payment failed. Please try again.');
    } finally {
      setPaying(false);
    }
  };

  if (success) {
    return (
      <Layout>
        <div className="max-w-md mx-auto text-center space-y-4 py-12">
          <div className="text-6xl">✅</div>
          <h2 className="text-2xl font-bold text-green-700">Payment Successful!</h2>
          <p className="text-gray-600">
            Your subscription has been extended. Your new expiry date is{' '}
            <strong>{result?.new_expiry ? new Date(result.new_expiry).toLocaleDateString() : '1 month from now'}</strong>.
          </p>
          <p className="text-sm text-gray-500">
            Username: <code className="bg-gray-100 px-2 py-0.5 rounded">{result?.username}</code>
          </p>
          <button onClick={() => navigate('/dashboard')}
            className="bg-indigo-600 text-white px-6 py-3 rounded-xl font-semibold hover:bg-indigo-700 transition"
          >
            Go to Dashboard
          </button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto space-y-6">
        <div>
          <h2 className="text-2xl font-bold">Choose Your Plan</h2>
          <p className="text-gray-500">Select a package and proceed with payment</p>
        </div>

        {myCreds.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-xl p-3 text-sm text-blue-700">
            Renewing subscription for <strong>{myCreds[0].username}</strong> ({myCreds[0].plan_name})
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {plans.map(plan => (
            <PackageCard
              key={plan.id}
              plan={plan}
              selected={selectedPlan?.id === plan.id}
              onSelect={() => setSelectedPlan(plan)}
              currencySymbol={company?.currency_symbol}
            />
          ))}
        </div>

        {selectedPlan && (
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
            <h3 className="text-lg font-semibold mb-3">Order Summary</h3>
            <div className="flex justify-between text-sm">
              <span>Plan: <strong>{selectedPlan.name}</strong></span>
              <span className="font-bold">{company?.currency_symbol} {selectedPlan.price_display ?? (selectedPlan.price_cents / 100).toFixed(0)}</span>
            </div>
            <div className="flex justify-between text-sm mt-2">
              <span>Duration</span>
              <span>1 Month (renews same date next month)</span>
            </div>
            <div className="flex justify-between text-sm mt-2">
              <span>PPPoE Username</span>
              <span className="font-mono text-xs">{myCreds.length > 0 ? myCreds[0].username : 'Will be assigned by admin'}</span>
            </div>
            <hr className="my-3" />
            <div className="flex justify-between font-bold text-lg">
              <span>Total</span>
              <span className="text-indigo-600">{company?.currency_symbol} {selectedPlan.price_display ?? (selectedPlan.price_cents / 100).toFixed(0)}</span>
            </div>
            <button
              onClick={handlePay}
              disabled={paying || myCreds.length === 0}
              className="mt-4 w-full bg-indigo-600 text-white py-3 rounded-xl font-semibold hover:bg-indigo-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {myCreds.length === 0
                ? 'No Subscription — Contact Admin'
                : paying
                  ? 'Processing Payment...'
                  : 'Pay Now (Simulated)'}
            </button>
            <p className="text-xs text-gray-400 text-center mt-2">
              This is a simulated payment. Clicking "Pay Now" will directly update your subscription in the database.
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
}
