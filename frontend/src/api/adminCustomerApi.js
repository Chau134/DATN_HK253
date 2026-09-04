import request from '../config/Connect';

export async function fetchAdminCustomers() {
    const response = await request.get('/admin/customers');
    return response.data || [];
}

export async function deleteAdminCustomer(customerId) {
    await request.delete(`/admin/customers/${customerId}`);
}
