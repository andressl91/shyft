﻿from numpy import random
import unittest

from shyft import api
from shyft.api import pt_gs_k
from shyft.api import pt_ss_k
from shyft.api import pt_hs_k
from shyft.api import hbv_stack


class RegionModel(unittest.TestCase):
    @staticmethod
    def build_model(model_t, parameter_t, model_size, num_catchments=1):

        cells = model_t.cell_t.vector_t()
        cell_area = 1000 * 1000
        region_parameter = parameter_t()
        for i in range(model_size):
            loc = (10000 * random.random(2)).tolist() + (500 * random.random(1)).tolist()
            gp = api.GeoPoint(*loc)
            cid = 0
            if num_catchments > 1:
                cid = random.randint(1, num_catchments)
            geo_cell_data = api.GeoCellData(gp, cell_area, cid, 0.9, api.LandTypeFractions(0.01, 0.05, 0.19, 0.3, 0.45))
            # geo_cell_data.land_type_fractions_info().set_fractions(glacier=0.01, lake=0.05, reservoir=0.19, forest=0.3)
            cell = model_t.cell_t()
            cell.geo = geo_cell_data
            cells.append(cell)

        return model_t(cells, region_parameter)

    @staticmethod
    def build_mock_state_dict(**kwargs):
        pt = {}
        gs = {"albedo": 0.4,
              "lwc": 0.1,
              "surface_heat": 30000,
              "alpha": 1.26,
              "sdc_melt_mean": 1.0,
              "acc_melt": 0.0,
              "iso_pot_energy": 0.0,
              "temp_swe": 0.0}
        kirchner = {"q": 0.25}
        pt.update({(k, v) for k, v in kwargs.items() if k in pt})
        gs.update({(k, v) for k, v in kwargs.items() if k in gs})
        kirchner.update({(k, v) for k, v in kwargs.items() if k in kirchner})
        state = pt_gs_k.PTGSKState()
        state.gs.albedo = gs["albedo"]
        state.gs.lwc = gs["lwc"]
        state.gs.surface_heat = gs["surface_heat"]
        state.gs.alpha = gs["alpha"]
        state.gs.sdc_melt_mean = gs["sdc_melt_mean"]
        state.gs.acc_melt = gs["acc_melt"]
        state.gs.iso_pot_energy = gs["iso_pot_energy"]
        state.gs.temp_swe = gs["temp_swe"]
        state.kirchner.q = kirchner["q"]
        return pt_gs_k.PTGSKStateIo().to_string(state)

    def _create_constant_geo_ts(self, geo_ts_type, geo_point, utc_period, value):
        """Create a time point ts, with one value at the start
        of the supplied utc_period."""
        tv = api.UtcTimeVector()
        tv.push_back(utc_period.start)
        vv = api.DoubleVector()
        vv.push_back(value)
        cts = api.TsFactory().create_time_point_ts(utc_period, tv, vv)
        return geo_ts_type(geo_point, cts)

    def test_source_uid(self):
        cal = api.Calendar()
        time_axis = api.Timeaxis(cal.time(api.YMDhms(2015, 1, 1, 0, 0, 0)), api.deltahours(1), 240)
        mid_point = api.GeoPoint(1000, 1000, 100)
        precip_source = self._create_constant_geo_ts(api.PrecipitationSource, mid_point, time_axis.total_period(), 5.0)
        self.assertIsNotNone(precip_source.uid)
        precip_source.uid = 'abc'
        self.assertEqual(precip_source.uid, 'abc')

    def create_dummy_region_environment(self, time_axis, mid_point):
        re = api.ARegionEnvironment()
        re.precipitation.append(self._create_constant_geo_ts(api.PrecipitationSource, mid_point, time_axis.total_period(), 5.0))
        re.temperature.append(self._create_constant_geo_ts(api.TemperatureSource, mid_point, time_axis.total_period(), 10.0))
        re.wind_speed.append(self._create_constant_geo_ts(api.WindSpeedSource, mid_point, time_axis.total_period(), 2.0))
        re.rel_hum.append(self._create_constant_geo_ts(api.RelHumSource, mid_point, time_axis.total_period(), 0.7))
        re.radiation = api.RadiationSourceVector()  # just for testing BW compat
        re.radiation.append(self._create_constant_geo_ts(api.RadiationSource, mid_point, time_axis.total_period(), 300.0))
        return re

    def test_create_region_environment(self):
        cal = api.Calendar()
        time_axis = api.Timeaxis(cal.time(api.YMDhms(2015, 1, 1, 0, 0, 0)), api.deltahours(1), 240)
        re = self.create_dummy_region_environment(time_axis, api.GeoPoint(1000, 1000, 100))
        self.assertIsNotNone(re)
        self.assertEqual(len(re.radiation), 1)
        self.assertAlmostEqual(re.radiation[0].ts.value(0), 300.0)

    def test_pt_ss_k_model_init(self):
        num_cells = 20
        model_type = pt_ss_k.PTSSKModel
        model = self.build_model(model_type, pt_ss_k.PTSSKParameter, num_cells)
        self.assertEqual(model.size(), num_cells)

    def test_pt_hs_k_model_init(self):
        num_cells = 20
        model_type = pt_hs_k.PTHSKModel
        model = self.build_model(model_type, pt_hs_k.PTHSKParameter, num_cells)
        self.assertEqual(model.size(), num_cells)

    def test_hbv_stack_model_init(self):
        num_cells = 20
        model_type = hbv_stack.HbvModel
        model = self.build_model(model_type, hbv_stack.HbvParameter, num_cells)
        self.assertEqual(model.size(), num_cells)

    def test_model_area_functions(self):
        num_cells = 20
        model_type = pt_gs_k.PTGSKModel
        model = self.build_model(model_type, pt_gs_k.PTGSKParameter, num_cells)
        # demo how to get area statistics.
        cids = api.IntVector()
        total_area = model.statistics.total_area(cids)
        forest_area = model.statistics.forest_area(cids)
        glacier_area = model.statistics.glacier_area(cids)
        lake_area = model.statistics.lake_area(cids)
        reservoir_area = model.statistics.reservoir_area(cids)
        unspecified_area = model.statistics.unspecified_area(cids)
        self.assertAlmostEqual(total_area, forest_area + glacier_area + lake_area + reservoir_area + unspecified_area)
        cids.append(3)
        total_area_no_match = model.statistics.total_area(cids)  # now, cids contains 3, that matches no cells
        self.assertAlmostEqual(total_area_no_match, 0.0)

    def test_model_initialize_and_run(self):
        num_cells = 20
        model_type = pt_gs_k.PTGSKModel
        model = self.build_model(model_type, pt_gs_k.PTGSKParameter, num_cells)
        self.assertEqual(model.size(), num_cells)
        # now modify snow_cv forest_factor to 0.1
        region_parameter = model.get_region_parameter()
        region_parameter.gs.snow_cv_forest_factor = 0.1
        region_parameter.gs.snow_cv_altitude_factor = 0.0001
        self.assertEqual(region_parameter.gs.snow_cv_forest_factor, 0.1)
        self.assertEqual(region_parameter.gs.snow_cv_altitude_factor, 0.0001)

        self.assertAlmostEqual(region_parameter.gs.effective_snow_cv(1.0, 0.0), region_parameter.gs.snow_cv + 0.1)
        self.assertAlmostEqual(region_parameter.gs.effective_snow_cv(1.0, 1000.0), region_parameter.gs.snow_cv + 0.1 + 0.1)
        cal = api.Calendar()
        time_axis = api.Timeaxis(cal.time(2015, 1, 1, 0, 0, 0), api.deltahours(1), 240)
        model_interpolation_parameter = api.InterpolationParameter()
        # degC/m, so -0.5 degC/100m
        model_interpolation_parameter.temperature_idw.default_temp_gradient = -0.005
        # if possible use closest neighbor points and solve gradient using equation,(otherwise default min/max height)
        model_interpolation_parameter.temperature_idw.gradient_by_equation = True
        # Max number of temperature sources used for one interpolation
        model_interpolation_parameter.temperature_idw.max_members = 6
        # 20 km is max distance
        model_interpolation_parameter.temperature_idw.max_distance = 20000
        # zscale is used to discriminate neighbors at different elevation than target point
        self.assertAlmostEqual(model_interpolation_parameter.temperature_idw.zscale, 1.0)
        model_interpolation_parameter.temperature_idw.zscale = 0.5
        self.assertAlmostEqual(model_interpolation_parameter.temperature_idw.zscale, 0.5)
        # Pure linear interpolation
        model_interpolation_parameter.temperature_idw.distance_measure_factor = 1.0
        # This enables IDW with default temperature gradient.
        model_interpolation_parameter.use_idw_for_temperature = True
        self.assertAlmostEqual(model_interpolation_parameter.precipitation.scale_factor, 1.02)  # just verify this one is as before change to scale_factor
        model.initialize_cell_environment(time_axis)  # just show how we can split the run_interpolation into two calls(second one optional)
        model.interpolate(
            model_interpolation_parameter,
            self.create_dummy_region_environment(time_axis,
                                                 model.get_cells()[int(num_cells / 2)].geo.mid_point()))
        m_ip_parameter = model.interpolation_parameter  # illustrate that we can get back the passed interpolation parameter as a property of the model
        self.assertEqual(m_ip_parameter.use_idw_for_temperature, True)  # just to ensure we really did get back what we passed in
        self.assertAlmostEqual(m_ip_parameter.temperature_idw.zscale, 0.5)
        s0 = pt_gs_k.PTGSKStateVector()
        for i in range(num_cells):
            si = pt_gs_k.PTGSKState()
            si.kirchner.q = 40.0
            s0.append(si)
        model.set_states(s0)
        model.set_state_collection(-1, True)  # enable state collection for all cells
        model2 = model_type(model)  # make a copy, so that we in the stepwise run below get a clean copy with all values zero.
        model.run_cells()  # the default arguments applies: thread_cell_count=0,start_step=0,n_steps=0)
        cids = api.IntVector()  # optional, we can add selective catchment_ids here
        sum_discharge = model.statistics.discharge(cids)
        sum_discharge_value = model.statistics.discharge_value(cids, 0)  # at the first timestep
        self.assertGreaterEqual(sum_discharge_value, 130.0)
        self.assertIsNotNone(sum_discharge)
        # now, re-run the process in 24-hours steps x 10
        model.set_states(s0)  # restore state s0
        for section in range(10):
            model2.run_cells(thread_cell_count=0, start_step=section*24, n_steps=24)
            section_discharge = model2.statistics.discharge(cids)
            self.assertEqual(section_discharge.size(),sum_discharge.size()) # notice here that the values after current step are 0.0
        stepwise_sum_discharge = model2.statistics.discharge(cids)
        # assert stepwise_sum_discharge == sum_discharge
        diff_ts = sum_discharge.values.to_numpy()-stepwise_sum_discharge.values.to_numpy()
        self.assertAlmostEqual((diff_ts*diff_ts).max(),0.0,4)
        # Verify that if we pass in illegal cids, then it raises exception(with first failing
        try:
            illegal_cids = api.IntVector([0, 4, 5])
            model.statistics.discharge(illegal_cids)
            self.assertFalse(True, "Failed test, using illegal cids should raise exception")
        except RuntimeError as rte:
            pass

        avg_temperature = model.statistics.temperature(cids)
        avg_precipitation = model.statistics.precipitation(cids)
        self.assertIsNotNone(avg_precipitation)
        for time_step in range(time_axis.size()):
            precip_raster = model.statistics.precipitation(cids, time_step)  # example raster output
            self.assertEqual(precip_raster.size(), num_cells)
        # example single value spatial aggregation (area-weighted) over cids for a specific timestep
        avg_gs_sc_value = model.gamma_snow_response.sca_value(cids, 1)
        self.assertGreaterEqual(avg_gs_sc_value, 0.0)
        avg_gs_sca = model.gamma_snow_response.sca(cids)  # swe output
        self.assertIsNotNone(avg_gs_sca)
        # lwc surface_heat alpha melt_mean melt iso_pot_energy temp_sw
        avg_gs_albedo = model.gamma_snow_state.albedo(cids)
        self.assertIsNotNone(avg_gs_albedo)
        self.assertEqual(avg_temperature.size(), time_axis.size(), "expect results equal to time-axis size")
        copy_region_model = model.__class__(model)
        self.assertIsNotNone(copy_region_model)
        copy_region_model.run_cells()  # just to verify we can copy and run the new model

    def test_optimization_model(self):
        num_cells = 20
        model_type = pt_gs_k.PTGSKOptModel
        model = self.build_model(model_type, pt_gs_k.PTGSKParameter, num_cells)
        cal = api.Calendar()
        t0 = cal.time(2015, 1, 1, 0, 0, 0)
        dt = api.deltahours(1)
        n = 240
        time_axis = api.Timeaxis(t0, dt, n)
        model_interpolation_parameter = api.InterpolationParameter()
        model.initialize_cell_environment(time_axis)  # just show how we can split the run_interpolation into two calls(second one optional)
        model.interpolate(
            model_interpolation_parameter,
            self.create_dummy_region_environment(time_axis,
                                                 model.get_cells()[int(num_cells / 2)].geo.mid_point()))
        s0 = pt_gs_k.PTGSKStateVector()
        for i in range(num_cells):
            si = pt_gs_k.PTGSKState()
            si.kirchner.q = 40.0
            s0.append(si)
        model.set_states(s0)  # at this point the intial state of model is established as well
        model.run_cells()
        cids = api.IntVector.from_numpy([0])  # optional, we can add selective catchment_ids here
        sum_discharge = model.statistics.discharge(cids)
        sum_discharge_value = model.statistics.discharge_value(cids, 0)  # at the first timestep
        self.assertGreaterEqual(sum_discharge_value, 130.0)
        # verify we can construct an optimizer
        optimizer = model_type.optimizer_t(model)  # notice that a model type know it's optimizer type, e.g. PTGSKOptimizer
        self.assertIsNotNone(optimizer)
        #
        # create target specification
        #
        model.revert_to_initial_state()  # set_states(s0)  # remember to set the s0 again, so we have the same initial condition for our game
        tsa = api.TsTransform().to_average(t0, dt, n, sum_discharge)
        t_spec_1 = api.TargetSpecificationPts(tsa, cids, 1.0, api.KLING_GUPTA, 1.0, 0.0, 0.0, api.DISCHARGE, 'test_uid')

        target_spec = api.TargetSpecificationVector()
        target_spec.append(t_spec_1)
        upper_bound = model_type.parameter_t(model.get_region_parameter())  # the model_type know it's parameter_t
        lower_bound = model_type.parameter_t(model.get_region_parameter())
        upper_bound.kirchner.c1 = -1.9
        lower_bound.kirchner.c1 = -3.0
        upper_bound.kirchner.c2 = 0.99
        lower_bound.kirchner.c2 = 0.80

        optimizer.set_target_specification(target_spec, lower_bound, upper_bound)
        # Not needed, it will automatically get one.
        #optimizer.establish_initial_state_from_model()
        #s0_0 = optimizer.get_initial_state(0)
        #optimizer.set_verbose_level(1000)
        p0 = model_type.parameter_t(model.get_region_parameter())
        orig_c1 = p0.kirchner.c1
        orig_c2 = p0.kirchner.c2
        # model.get_cells()[0].env_ts.precipitation.set(0, 5.1)
        # model.get_cells()[0].env_ts.precipitation.set(1, 4.9)
        p0.kirchner.c1 = -2.4
        p0.kirchner.c2 = 0.91
        opt_param = optimizer.optimize(p0, 1500, 0.1, 1e-5)
        goal_fx = optimizer.calculate_goal_function(opt_param)
        p0.kirchner.c1 = -2.4
        p0.kirchner.c2 = 0.91
        #goal_fx1 = optimizer.calculate_goal_function(p0)

        self.assertLessEqual(goal_fx, 10.0)
        self.assertAlmostEqual(orig_c1, opt_param.kirchner.c1, 4)
        self.assertAlmostEqual(orig_c2, opt_param.kirchner.c2, 4)


    def test_hbv_model_initialize_and_run(self):
        num_cells = 20
        model_type = hbv_stack.HbvModel
        model = self.build_model(model_type, hbv_stack.HbvParameter, num_cells)
        self.assertEqual(model.size(), num_cells)
        # now modify snow_cv forest_factor to 0.1
        region_parameter = model.get_region_parameter()
        # region_parameter.gs.snow_cv_forest_factor = 0.1
        # region_parameter.gs.snow_cv_altitude_factor = 0.0001
        # self.assertEqual(region_parameter.gs.snow_cv_forest_factor, 0.1)
        # self.assertEqual(region_parameter.gs.snow_cv_altitude_factor, 0.0001)

        # self.assertAlmostEqual(region_parameter.gs.effective_snow_cv(1.0, 0.0), region_parameter.gs.snow_cv + 0.1)
        # self.assertAlmostEqual(region_parameter.gs.effective_snow_cv(1.0, 1000.0), region_parameter.gs.snow_cv + 0.1 + 0.1)
        cal = api.Calendar()
        time_axis = api.Timeaxis(cal.time(2015, 1, 1, 0, 0, 0), api.deltahours(1), 240)
        model_interpolation_parameter = api.InterpolationParameter()
        # degC/m, so -0.5 degC/100m
        model_interpolation_parameter.temperature_idw.default_temp_gradient = -0.005
        # if possible use closest neighbor points and solve gradient using equation,(otherwise default min/max height)
        model_interpolation_parameter.temperature_idw.gradient_by_equation = True
        # Max number of temperature sources used for one interpolation
        model_interpolation_parameter.temperature_idw.max_members = 6
        # 20 km is max distance
        model_interpolation_parameter.temperature_idw.max_distance = 20000
        # zscale is used to discriminate neighbors at different elevation than target point
        self.assertAlmostEqual(model_interpolation_parameter.temperature_idw.zscale, 1.0)
        model_interpolation_parameter.temperature_idw.zscale = 0.5
        self.assertAlmostEqual(model_interpolation_parameter.temperature_idw.zscale, 0.5)
        # Pure linear interpolation
        model_interpolation_parameter.temperature_idw.distance_measure_factor = 1.0
        # This enables IDW with default temperature gradient.
        model_interpolation_parameter.use_idw_for_temperature = True
        self.assertAlmostEqual(model_interpolation_parameter.precipitation.scale_factor, 1.02)  # just verify this one is as before change to scale_factor
        model.run_interpolation(
            model_interpolation_parameter, time_axis,
            self.create_dummy_region_environment(time_axis,
                                                 model.get_cells()[int(num_cells / 2)].geo.mid_point()))
        s0 = hbv_stack.HbvStateVector()
        for i in range(num_cells):
            si = hbv_stack.HbvState()
            si.tank.uz = 40.0
            si.tank.lz = 40.0
            s0.append(si)
        model.set_states(s0)
        model.set_state_collection(-1, True)  # enable state collection for all cells
        model.run_cells()
        cids = api.IntVector()  # optional, we can add selective catchment_ids here
        sum_discharge = model.statistics.discharge(cids)
        sum_discharge_value = model.statistics.discharge_value(cids, 0)  # at the first timestep
        self.assertGreaterEqual(sum_discharge_value, 32.0)
        self.assertIsNotNone(sum_discharge)
        # Verify that if we pass in illegal cids, then it raises exception(with first failing
        try:
            illegal_cids = api.IntVector([0, 4, 5])
            model.statistics.discharge(illegal_cids)
            self.assertFalse(True, "Failed test, using illegal cids should raise exception")
        except RuntimeError as rte:
            pass

        avg_temperature = model.statistics.temperature(cids)
        avg_precipitation = model.statistics.precipitation(cids)
        self.assertIsNotNone(avg_precipitation)
        for time_step in range(time_axis.size()):
            precip_raster = model.statistics.precipitation(cids, time_step)  # example raster output
            self.assertEqual(precip_raster.size(), num_cells)
        # example single value spatial aggregation (area-weighted) over cids for a specific timestep
        # avg_gs_sc_value = model.gamma_snow_response.sca_value(cids, 1)
        # self.assertGreaterEqual(avg_gs_sc_value,0.0)
        # avg_gs_sca = model.gamma_snow_response.sca(cids)  # swe output
        # self.assertIsNotNone(avg_gs_sca)
        # lwc surface_heat alpha melt_mean melt iso_pot_energy temp_sw
        # avg_gs_albedo = model.gamma_snow_state.albedo(cids)
        # self.assertIsNotNone(avg_gs_albedo)
        self.assertEqual(avg_temperature.size(), time_axis.size(), "expect results equal to time-axis size")
        copy_region_model = model.__class__(model)
        self.assertIsNotNone(copy_region_model)
        copy_region_model.run_cells()  # just to verify we can copy and run the new model

    def test_model_state_io(self):
        num_cells = 2
        for model_type in [pt_gs_k.PTGSKModel, pt_gs_k.PTGSKOptModel]:
            model = self.build_model(model_type, pt_gs_k.PTGSKParameter, num_cells)
            state_list = []
            x = ""
            for i in range(num_cells):
                state_list.append(self.build_mock_state_dict(q=(i + 1) * 0.5 / num_cells))
            initial_states = x.join(state_list)
            sio = model_type.state_t.serializer_t()
            state_vector = sio.vector_from_string(initial_states)
            model.set_states(state_vector)
            m_state_vector = model_type.state_t.vector_t()
            model.get_states(m_state_vector)
            retrieved_states = sio.to_string(m_state_vector)
            self.assertEqual(initial_states, retrieved_states)

    def test_set_too_few_model_states(self):
        num_cells = 20
        for model_type in [pt_gs_k.PTGSKModel, pt_gs_k.PTGSKOptModel]:
            model = self.build_model(model_type, pt_gs_k.PTGSKParameter, num_cells)

            states = []
            x = ""
            for i in range(num_cells - 1):
                states.append(self.build_mock_state_dict(q=(i + 1) * 0.5 / num_cells))
            statestr = x.join(states)
            sio = model_type.state_t.serializer_t()
            state_vector = sio.vector_from_string(statestr)

            self.assertRaises(RuntimeError, model.set_states, state_vector)
            for i in range(num_cells + 1):
                states.append(self.build_mock_state_dict(q=(i + 1) * 0.5 / num_cells))
            statestr = x.join(states)
            state_vector = sio.vector_from_string(statestr)

            self.assertRaises(RuntimeError, model.set_states, state_vector)

    def test_geo_cell_data_serializer(self):
        """
        This test the bulding block for the geo-cell caching mechanism that can be
        implemented in GeoCell repository to cache complex information from the GIS system.
        The test illustrates how to convert existing cell-vector geo info into a DoubleVector,
        that can be converted .to_nump(),
        and then how to re-create the cell-vector,(of any given type actually) based on
        the geo-cell data DoubleVector (that can be created from .from_numpy(..)

        Notice that the from_numpy(np array) could have limited functionality when it comes
        to strides etc, so if problem flatten out the np.array before passing it.

        """
        n_cells = 3
        n_values_pr_gcd = 11  # number of values in a geo_cell_data stride
        model = self.build_model(pt_gs_k.PTGSKModel, pt_gs_k.PTGSKParameter, n_cells)
        cell_vector = model.get_cells()
        geo_cell_data_vector = cell_vector.geo_cell_data_vector(cell_vector)  # This gives a string, ultra fast, containing the serialized form of all geo-cell data
        self.assertEqual(len(geo_cell_data_vector), n_values_pr_gcd * n_cells)
        cell_vector2 = pt_gs_k.PTGSKCellAllVector.create_from_geo_cell_data_vector(
            geo_cell_data_vector)  # This gives a cell_vector, of specified type, with exactly the same geo-cell data as the original
        self.assertEqual(len(cell_vector), len(cell_vector2))  # just verify equal size, and then geometry, the remaining tests are covered by C++ testing
        for i in range(len(cell_vector)):
            self.assertAlmostEqual(cell_vector[i].geo.mid_point().z, cell_vector2[i].mid_point().z)
            self.assertAlmostEqual(cell_vector[i].geo.mid_point().x, cell_vector2[i].mid_point().x)
            self.assertAlmostEqual(cell_vector[i].geo.mid_point().y, cell_vector2[i].mid_point().y)


if __name__ == "__main__":
    unittest.main()
